import os
import sys
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

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


class MockObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_finalize_round_success():
    """Test 1: Chốt vòng thi thành công và kiểm tra response structure, total_score, rank."""
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    mock_result = {
        "message": "Round finalized successfully",
        "round_id": 1,
        "status": "FINALIZED",
        "results": [
            {
                "user_id": 10,
                "submission_id": 101,
                "total_score": 95.5,
                "rank": 1
            },
            {
                "user_id": 15,
                "submission_id": 102,
                "total_score": 90.0,
                "rank": 2
            }
        ]
    }

    with patch('src.services.score_service.ScoreService.finalize_round', return_value=(mock_result, None)):
        res = client.post('/rounds/1/finalize', headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 200
    data = res.get_json()
    assert data['round_id'] == 1
    assert data['status'] == 'FINALIZED'
    assert len(data['results']) == 2
    assert data['results'][0]['user_id'] == 10
    assert data['results'][0]['rank'] == 1
    assert data['results'][0]['total_score'] == 95.5
    assert data['results'][1]['user_id'] == 15
    assert data['results'][1]['rank'] == 2
    assert data['results'][1]['total_score'] == 90.0


def test_finalize_round_organizer_endpoint():
    """Test alias route /organizer/contests/1/rounds/1/finalize."""
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    mock_result = {
        "message": "Round finalized successfully",
        "round_id": 1,
        "status": "FINALIZED",
        "results": []
    }

    with patch('src.services.score_service.ScoreService.finalize_round', return_value=(mock_result, None)):
        res = client.post('/organizer/contests/1/rounds/1/finalize', headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'FINALIZED'


def test_finalize_round_not_found():
    """Test 2: Vòng thi không tồn tại (404)."""
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    with patch('src.services.score_service.ScoreService.finalize_round', return_value=(None, 'round_not_found')):
        res = client.post('/rounds/999/finalize', headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 404
    data = res.get_json()
    assert 'Không tìm thấy vòng thi' in data['message']


def test_finalize_round_already_finalized():
    """Test 3: Vòng thi đã được chốt trước đó (400)."""
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='organizer')

    with patch('src.services.score_service.ScoreService.finalize_round', return_value=(None, 'round_already_finalized')):
        res = client.post('/rounds/1/finalize', headers={'Authorization': f'Bearer {token}'})

    assert res.status_code == 400
    data = res.get_json()
    assert 'đã được chốt' in data['message']


def test_finalize_round_unauthorized():
    """Test authorization: Thiếu JWT token (401)."""
    app = create_app()
    client = app.test_client()
    res = client.post('/rounds/1/finalize')
    assert res.status_code == 401


def test_finalize_round_forbidden_role():
    """Test permissions: Role participant không thể chốt điểm (403)."""
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), role='participant')
    res = client.post('/rounds/1/finalize', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


def test_score_calculation_and_ranking_logic():
    """Test 4 & 5: Kiểm tra tính toán tổng điểm và xếp hạng từ cao xuống thấp của ScoreService.finalize_round."""
    from src.services.score_service import ScoreService

    # Mock repositories
    mock_contest_repo = MagicMock()
    mock_submission_repo = MagicMock()
    mock_score_repo = MagicMock()

    # Mock Round
    mock_round = MockObj(id=1, contest_id=10, title="Vòng 1", status="ongoing")
    mock_contest_repo.get_round_by_id.return_value = mock_round

    # Mock Criteria for round 1
    mock_crit1 = MockObj(id=1, round_id=1, name="Bố cục", weight=2.0)
    mock_crit2 = MockObj(id=2, round_id=1, name="Màu sắc", weight=1.0)
    mock_contest_repo.get_criteria_by_round_id.return_value = [mock_crit1, mock_crit2]

    # Mock Submissions for round 1 (Candidate A: user 10, Candidate B: user 15, Candidate C: user 20)
    subA = MockObj(id=101, round_id=1, user_id=10, final_score=None, status='submitted', submitted_at=datetime(2026, 1, 1, 10, 0))
    subB = MockObj(id=102, round_id=1, user_id=15, final_score=None, status='submitted', submitted_at=datetime(2026, 1, 1, 11, 0))
    subC = MockObj(id=103, round_id=1, user_id=20, final_score=None, status='submitted', submitted_at=datetime(2026, 1, 1, 12, 0))

    mock_submission_repo.list.return_value = [subA, subB, subC]
    mock_submission_repo.session = None
    mock_contest_repo.session = None

    # Scores for SubA (Judge 1: Crit1=9.0 (w=2), Crit2=6.0 (w=1) -> weighted avg = (9*2+6*1)/3 = 8.0)
    scoresA = [
        MockObj(submission_id=101, judge_id=1, criteria_id=1, score_value=9.0),
        MockObj(submission_id=101, judge_id=1, criteria_id=2, score_value=6.0),
    ]

    # Scores for SubB (Judge 1: Crit1=10.0 (w=2), Crit2=10.0 (w=1) -> weighted avg = (10*2+10*1)/3 = 10.0)
    scoresB = [
        MockObj(submission_id=102, judge_id=1, criteria_id=1, score_value=10.0),
        MockObj(submission_id=102, judge_id=1, criteria_id=2, score_value=10.0),
    ]

    # Scores for SubC (Judge 1: Crit1=8.0 (w=2), Crit2=8.0 (w=1) -> weighted avg = 8.0)
    scoresC = [
        MockObj(submission_id=103, judge_id=1, criteria_id=1, score_value=8.0),
        MockObj(submission_id=103, judge_id=1, criteria_id=2, score_value=8.0),
    ]

    def list_scores_side_effect(sub_id):
        if sub_id == 101: return scoresA
        if sub_id == 102: return scoresB
        if sub_id == 103: return scoresC
        return []

    mock_score_repo.list_by_submission.side_effect = list_scores_side_effect

    service = ScoreService(
        score_repo=mock_score_repo,
        submission_repo=mock_submission_repo,
        contest_repo=mock_contest_repo
    )

    data, error = service.finalize_round(1)

    assert error is None
    assert data['round_id'] == 1
    assert data['status'] == 'FINALIZED'
    results = data['results']
    assert len(results) == 3

    # Rank 1: subB (user 15) with score 10.0
    assert results[0]['user_id'] == 15
    assert results[0]['total_score'] == 10.0
    assert results[0]['rank'] == 1

    # Rank 2: subA (user 10) and subC (user 20) both have score 8.0
    assert results[1]['total_score'] == 8.0
    assert results[1]['rank'] == 2
    assert results[2]['total_score'] == 8.0
    assert results[2]['rank'] == 2

    # Verify contest_repo updated round status
    mock_contest_repo.update_round.assert_called_with(1, {'status': 'FINALIZED'})