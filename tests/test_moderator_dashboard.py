import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app
import api.controllers.moderator_controller as moderator_controller
from services.moderator_dashboard_service import ModeratorDashboardService


def token(app, user_id, role):
    return jwt.encode(
        {
            'user_id': user_id,
            'role': role,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        },
        app.config['SECRET_KEY'],
        algorithm='HS256',
    )


def test_moderator_dashboard_endpoint_returns_metrics_and_queue():
    app = create_app()
    service = MagicMock()
    service.dashboard.return_value = {
        'contest_count': 1,
        'participant_count': 3,
        'submission_count': 5,
        'judge_assignment_count': 2,
        'submission_statuses': {'submitted': 2, 'flagged': 1, 'evaluated': 2, 'rejected': 0},
        'ai_risk_counts': {'safe': 2, 'medium': 1, 'high': 1},
        'pending_ai_review_count': 1,
    }
    service.submissions.return_value = {
        'submissions': [{'id': 10, 'status': 'flagged', 'needs_review': True}],
        'pagination': {'page': 2, 'per_page': 10, 'total': 1, 'pages': 1},
    }
    original = moderator_controller.moderator_service
    moderator_controller.moderator_service = service
    try:
        client = app.test_client()
        headers = {'Authorization': f"Bearer {token(app, 7, 'organizer')}"}
        response = client.get('/moderator/dashboard?contest_id=4', headers=headers)
        assert response.status_code == 200
        assert response.get_json()['submission_statuses']['flagged'] == 1
        service.dashboard.assert_called_once_with(7, 'organizer', 4)

        response = client.get(
            '/moderator/submissions?contest_id=4&page=2&per_page=10&status=flagged&ai_risk=high',
            headers=headers,
        )
        assert response.status_code == 200
        assert response.get_json()['submissions'][0]['needs_review'] is True
        service.submissions.assert_called_once_with(7, 'organizer', 4, 2, 10, 'flagged', 'high')
    finally:
        moderator_controller.moderator_service = original


def test_moderator_endpoints_require_organizer_or_admin():
    app = create_app()
    client = app.test_client()
    headers = {'Authorization': f"Bearer {token(app, 7, 'participant')}"}
    assert client.get('/moderator/dashboard', headers=headers).status_code == 403
    assert client.get('/moderator/submissions', headers=headers).status_code == 403


class FakeDashboardRepository:
    def __init__(self):
        self.session = MagicMock()

    def contest_ids_for_user(self, user_id):
        return [11, 12]

    def contest_exists(self, contest_id):
        return contest_id == 99

    def all_contest_ids(self):
        return [99, 100]

    def dashboard_metrics(self, contest_ids):
        return {'contest_ids': contest_ids}

    def review_queue(self, contest_ids, page, per_page, status, ai_risk):
        return [], 0


def test_service_scopes_organizer_and_admin_contests():
    repository = FakeDashboardRepository()
    service = ModeratorDashboardService(repository)

    assert service.dashboard(7, 'organizer')['contest_ids'] == [11, 12]
    assert service.dashboard(7, 'organizer', 11)['contest_ids'] == [11]
    assert service.dashboard(1, 'admin', 99)['contest_ids'] == [99]
    assert service.dashboard(1, 'admin')['contest_ids'] == [99, 100]

    try:
        service.dashboard(7, 'organizer', 99)
        assert False, 'organizer should not access another contest'
    except PermissionError:
        pass