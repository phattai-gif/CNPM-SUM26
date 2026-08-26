import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest

from domain.contest import Contest
from services.contest_service import ContestService


class MemoryContestRepository:
    def __init__(self):
        self.contest = Contest(
            id=10,
            title='Photo Contest',
            slug='photo-contest',
            created_by=7,
            categories=[],
            awards=[],
        )

    def get_contest_by_id(self, contest_id):
        return self.contest if contest_id == self.contest.id else None

    def update_contest(self, contest_id, data):
        if 'categories_json' in data:
            self.contest.categories = data['categories_json']
        if 'awards_json' in data:
            self.contest.awards = data['awards_json']
        return self.contest


def test_category_and_award_crud_is_scoped_to_contest_owner():
    repository = MemoryContestRepository()
    service = ContestService(repository)

    categories = service.create_category(
        10, {'name': 'Portrait', 'description': 'People photography'}, 7
    )
    assert categories[0] == {
        'id': 1,
        'name': 'Portrait',
        'description': 'People photography',
    }

    awards = service.create_award(
        10,
        {'title': 'First Prize', 'prize': '10,000,000 VND', 'quantity': 2},
        7,
    )
    assert awards[0]['quantity'] == 2
    assert awards[0]['rank'] == 1

    updated_awards = service.update_award(10, 1, {'quantity': 3}, 7)
    assert updated_awards[0]['quantity'] == 3

    assert service.delete_category(10, 1, 7) == []
    assert service.delete_award(10, 1, 7) == []

    with pytest.raises(PermissionError):
        service.create_category(10, {'name': 'Unauthorized'}, 99)


def test_award_quantity_is_at_least_one():
    repository = MemoryContestRepository()
    service = ContestService(repository)

    awards = service.create_award(10, {'title': 'Prize', 'quantity': 0}, 7)
    assert awards[0]['quantity'] == 1
