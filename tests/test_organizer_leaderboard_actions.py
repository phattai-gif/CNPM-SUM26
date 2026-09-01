import os
import sys
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app


def generate_token(secret_key, user_id=1, username='organizer1', role='organizer'):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def test_approve_winner_updates_status_and_commits():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    # Prepare mock session and submission
    from src.api.controllers import contest_controller as cc

    session = MagicMock()
    mock_sub = MagicMock()
    mock_sub.id = 555
    mock_sub.status = 'submitted'

    # session.query(...).filter(...).first() -> mock_sub
    session.query.return_value.filter.return_value.first.return_value = mock_sub

    # attach session to contest_service repository
    cc.contest_service.repository.session = session

    res = client.post(f'/organizer/submissions/{mock_sub.id}/approve-winner', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['message'] == 'Winner approved'
    assert data['submission_status'] == 'winner_approved'
    # commit was called
    assert session.commit.called


def test_reject_winner_updates_status_and_commits():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    from src.api.controllers import contest_controller as cc

    session = MagicMock()
    mock_sub = MagicMock()
    mock_sub.id = 556
    mock_sub.status = 'submitted'

    session.query.return_value.filter.return_value.first.return_value = mock_sub
    cc.contest_service.repository.session = session

    res = client.post(f'/organizer/submissions/{mock_sub.id}/reject-winner', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['message'] == 'Winner rejected'
    assert data['submission_status'] == 'winner_rejected'
    assert session.commit.called


def test_publish_creates_exhibit_and_returns_exhibit_id_and_image():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    from src.api.controllers import contest_controller as cc
    from infrastructure.models.app import SubmissionFileModel

    session = MagicMock()
    # First query for SubmissionModel -> return mock submission with round_id
    mock_sub = MagicMock()
    mock_sub.id = 557
    mock_sub.round_id = 42

    # Query for RoundModel to get contest_id
    mock_round = MagicMock()
    mock_round.contest_id = 99

    # Query for existing DigitalArchiveExhibitModel -> return None (not published)
    # To differentiate, make query.side_effect return objects depending on model arg
    def query_side_effect(model):
        q = MagicMock()
        if model.__name__ == 'SubmissionModel':
            q.filter.return_value.first.return_value = mock_sub
        elif model.__name__ == 'RoundModel':
            q.filter.return_value.first.return_value = mock_round
        elif model.__name__ == 'DigitalArchiveExhibitModel':
            q.filter.return_value.first.return_value = None
        elif model.__name__ == 'SubmissionFileModel':
            # return a fake file row with thumbnail/image url
            fake_file = MagicMock()
            fake_file.thumbnail_url = 'https://example.com/thumb.jpg'
            fake_file.image_hd_url = 'https://example.com/hd.jpg'
            q.filter.return_value.order_by.return_value.first.return_value = fake_file
        else:
            q.filter.return_value.first.return_value = None
        return q

    session.query.side_effect = query_side_effect
    cc.contest_service.repository.session = session

    res = client.post(f'/organizer/submissions/{mock_sub.id}/publish', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code in (200, 201)
    data = res.get_json()
    assert 'exhibit_id' in data
    # image_url may be present (we try to enrich)
    assert 'image_url' in data


def test_archive_submission_sets_status_archived():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    from src.api.controllers import contest_controller as cc

    session = MagicMock()
    mock_sub = MagicMock()
    mock_sub.id = 558
    mock_sub.status = 'published'

    session.query.return_value.filter.return_value.first.return_value = mock_sub
    cc.contest_service.repository.session = session

    res = client.post(f'/organizer/submissions/{mock_sub.id}/archive', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['message'] == 'Submission archived'
    assert data['submission_status'] == 'archived'
    assert session.commit.called


def test_get_round_leaderboard_uses_score_service_and_returns_leaderboard():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    mock_result = {
        "message": "Round finalized successfully",
        "round_id": 777,
        "status": "FINALIZED",
        "leaderboard": [
            {"rank": 1, "submission_id": 1001, "user_id": 10, "final_score": 98.5},
            {"rank": 2, "submission_id": 1002, "user_id": 11, "final_score": 95.0},
        ],
    }

    with patch('src.services.score_service.ScoreService.finalize_round', return_value=(mock_result, None)):
        res = client.get('/organizer/rounds/777/leaderboard', headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 200
    data = res.get_json()
    assert 'leaderboard' in data
    assert isinstance(data['leaderboard'], list)
    assert data['round_id'] == 777
    assert data['leaderboard'][0]['submission_id'] == 1001
    assert data['leaderboard'][1]['final_score'] == 95.0
