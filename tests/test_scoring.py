import os
import sys
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Set dummy DB URL for test
os.environ['POSTGREE_DATABASE_URL'] = 'sqlite:///:memory:'


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app


def generate_token(secret_key, user_id=1, username='judge1', role='judge'):
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


class MockObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_submit_score_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    mock_score = MockObj(id=1, submission_id=1, judge_id=1, criteria_id=2, score_value=8.5, comment='good')

    with patch('api.controllers.submission_controller.score_service.submit_score', return_value=(mock_score, None)):
        res = client.post('/submissions/1/scores', json={'criteria_id': 2, 'score_value': 8.5, 'comment': 'good'}, headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 200
    data = res.get_json()
    assert data['score']['score_value'] == 8.5


def test_submit_score_unauthorized():
    app = create_app()
    client = app.test_client()
    res = client.post('/submissions/1/scores', json={'criteria_id': 2, 'score_value': 8.5})
    assert res.status_code == 401


def test_submit_score_forbidden_non_judge():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='participant')
    res = client.post('/submissions/1/scores', json={'criteria_id': 2, 'score_value': 8.5}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


def test_submit_score_submission_not_found():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))
    with patch('api.controllers.submission_controller.score_service.submit_score', return_value=(None, 'submission_not_found')):
        res = client.post('/submissions/999/scores', json={'criteria_id': 2, 'score_value': 8.5}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 404


def test_submit_score_invalid_score():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))
    with patch('api.controllers.submission_controller.score_service.submit_score', return_value=(None, 'invalid_score')):
        res = client.post('/submissions/1/scores', json={'criteria_id': 2, 'score_value': 'bad'}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400


def test_submit_feedback_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    mock_fb = MockObj(id=1, submission_id=1, judge_id=1, summary_feedback='nice', final_recommendation='approve')
    with patch('api.controllers.submission_controller.score_service.submit_feedback', return_value=(mock_fb, None)):
        res = client.post('/submissions/1/feedback', json={'summary_feedback': 'nice', 'final_recommendation': 'approve'}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['feedback']['summary_feedback'] == 'nice'


def test_submit_feedback_unauthorized():
    app = create_app()
    client = app.test_client()
    res = client.post('/submissions/1/feedback', json={'summary_feedback': 'nice'})
    assert res.status_code == 401


def test_next_previous_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))
    with patch('api.controllers.submission_controller.score_service.get_next_previous', return_value=({'previous': None, 'next': 2}, None)):
        res = client.get('/submissions/1/next', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['next'] == 2


def test_next_previous_not_found():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))
    with patch('api.controllers.submission_controller.score_service.get_next_previous', return_value=(None, 'submission_not_found')):
        res = client.get('/submissions/999/next', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 404


def test_calculate_submission_score_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')
    mock_sub = MockObj(id=10, final_score=8.45)
    with patch('api.controllers.submission_controller.score_service.calculate_submission_score', return_value=(mock_sub, None)):
        res = client.post('/submissions/10/calculate-score', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['submission']['id'] == 10
    assert data['submission']['final_score'] == 8.45


def test_calculate_submission_score_not_found():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')
    with patch('api.controllers.submission_controller.score_service.calculate_submission_score', return_value=(None, 'submission_not_found')):
        res = client.post('/submissions/999/calculate-score', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 404


def test_submit_score_missing_criteria_id():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))
    res = client.post('/submissions/1/scores', json={'score_value': 8.5}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400
    assert 'criteria_id is required' in res.get_json()['message']


def test_submit_score_missing_score_value():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))
    res = client.post('/submissions/1/scores', json={'criteria_id': 2}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400
    assert 'score_value is required' in res.get_json()['message']


def test_submit_feedback_missing_summary():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))
    res = client.post('/submissions/1/feedback', json={'final_recommendation': 'approve'}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400
    assert 'summary_feedback is required' in res.get_json()['message']


def test_submit_score_judge_not_assigned():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=99)
    with patch('api.controllers.submission_controller.score_service.is_judge_assigned', return_value=False):
        res = client.post('/submissions/1/scores', json={'criteria_id': 2, 'score_value': 8.5}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403
    assert 'not assigned' in res.get_json()['message']

