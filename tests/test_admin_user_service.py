import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.admin_user_service import AdminUserService


class FakeAdminUserRepository:
    def __init__(self):
        self.calls = []

    def list_users(self, page, per_page, search, role, status):
        self.calls.append(('list', page, per_page, search, role, status))
        return [], 0

    def get_user(self, user_id):
        return {'id': user_id}

    def set_role(self, user_id, role):
        self.calls.append(('role', user_id, role))
        return {'id': user_id, 'role': role}

    def set_status(self, user_id, status):
        self.calls.append(('status', user_id, status))
        return {'id': user_id, 'status': status}


def test_admin_can_change_role_and_status():
    repository = FakeAdminUserRepository()
    service = AdminUserService(repository)

    assert service.change_role(1, 2, 'judge') == {'id': 2, 'role': 'judge'}
    assert service.change_status(1, 2, 'locked') == {'id': 2, 'status': 'locked'}
    assert repository.calls == [('role', 2, 'judge'), ('status', 2, 'locked')]


@pytest.mark.parametrize('method, value', [
    ('change_role', 'owner'),
    ('change_status', 'disabled'),
])
def test_admin_rejects_unknown_values(method, value):
    service = AdminUserService(FakeAdminUserRepository())
    with pytest.raises(ValueError):
        getattr(service, method)(1, 2, value)


def test_admin_cannot_change_own_role_or_status():
    service = AdminUserService(FakeAdminUserRepository())
    with pytest.raises(ValueError):
        service.change_role(7, 7, 'participant')
    with pytest.raises(ValueError):
        service.change_status(7, 7, 'locked')


def test_list_users_rejects_unknown_filters():
    service = AdminUserService(FakeAdminUserRepository())
    with pytest.raises(ValueError):
        service.list_users(role='owner')
    with pytest.raises(ValueError):
        service.list_users(status='disabled')