import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app
import api.controllers.submission_controller as submission_controller_module


def patch_controller_attr(attr_name, value):
    for mod_name in ['src.api.controllers.submission_controller', 'api.controllers.submission_controller']:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            setattr(mod, attr_name, value)


def generate_jwt_token(secret_key, user_id=5, username='participant_john', role='participant'):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=2)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


class MockSubObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_get_my_submissions_success():
    """Test Participant retrieving their own list of submissions from DB."""
    app = create_app()
    client = app.test_client()
    secret = app.config.get('SECRET_KEY', 'dev-secret-key-change-me-in-production-32chars')
    token = generate_jwt_token(secret, user_id=10, role='participant')

    mock_submissions = [
        {
            "id": 101,
            "title": "Bình Minh Trên Đồi Chè",
            "story_description": "Chụp bằng máy film cơ tại Cầu Đất",
            "status": "submitted",
            "final_score": 91.5,
            "submitted_at": "2026-08-15T08:30:00",
            "created_at": "2026-08-15T08:00:00",
            "round_id": 1,
            "round_title": "Vòng 1: Phong Cảnh Thiên Nhiên",
            "round_number": 1,
            "contest_id": 1,
            "contest_title": "Cuộc Thi Ảnh Phim Toàn Quốc 2026",
            "thumbnail_url": "https://images.unsplash.com/photo-1501785888041-af3ef285b470",
            "image_hd_url": "https://images.unsplash.com/photo-1501785888041-af3ef285b470",
            "ai_flag": {
                "confidence_score": 5.0,
                "risk_level": "safe",
                "status": "approved"
            }
        },
        {
            "id": 102,
            "title": "Phố Đêm Mưa Nháp",
            "story_description": "Ảnh nháp đang thử tone màu",
            "status": "draft",
            "final_score": None,
            "submitted_at": None,
            "created_at": "2026-08-18T20:00:00",
            "round_id": 2,
            "round_title": "Vòng 2: Đời Sống Đường Phố",
            "round_number": 2,
            "contest_id": 1,
            "contest_title": "Cuộc Thi Ảnh Phim Toàn Quốc 2026",
            "thumbnail_url": None,
            "image_hd_url": None,
            "ai_flag": None
        }
    ]

    with patch.object(submission_controller_module.submission_service, 'get_my_submissions', return_value=mock_submissions):
        response = client.get(
            '/submissions/my-submissions',
            headers={'Authorization': f'Bearer {token}'}
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'My submissions retrieved successfully'
    assert len(data['submissions']) == 2
    assert data['submissions'][0]['title'] == 'Bình Minh Trên Đồi Chè'
    assert data['submissions'][0]['contest_title'] == 'Cuộc Thi Ảnh Phim Toàn Quốc 2026'
    assert data['submissions'][0]['status'] == 'submitted'
    assert data['submissions'][1]['status'] == 'draft'


def test_get_submission_detail_authorized_owner():
    """Test Participant viewing their own submission details (with scores, film metadata, AI report)."""
    app = create_app()
    client = app.test_client()
    secret = app.config.get('SECRET_KEY', 'dev-secret-key-change-me-in-production-32chars')
    token = generate_jwt_token(secret, user_id=10, role='participant')

    mock_detail = {
        "id": 101,
        "user_id": 10,
        "round_id": 1,
        "title": "Bình Minh Trên Đồi Chè",
        "story_description": "Chụp bằng Leica M6",
        "status": "graded",
        "final_score": 91.5,
        "submitted_at": "2026-08-15T08:30:00",
        "created_at": "2026-08-15T08:00:00",
        "contest": {
            "id": 1,
            "title": "Cuộc Thi Ảnh Phim Toàn Quốc 2026"
        },
        "round": {
            "id": 1,
            "title": "Vòng 1: Phong Cảnh Thiên Nhiên",
            "round_number": 1
        },
        "file": {
            "image_hd_url": "https://example.com/photo.jpg",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "width_px": 3000,
            "height_px": 2000,
            "file_size_bytes": 4500000,
            "file_hash": "sha256hash123"
        },
        "film_metadata": {
            "film_stock": "Kodak Portra 400",
            "film_iso": 400,
            "camera_body": "Leica M6",
            "lens": "Summicron 35mm f/2",
            "lab_name": "Llab Vietnam",
            "scanner_info": "Noritsu HS-1800",
            "development_process": "C-41",
            "taken_at_location": "Đà Lạt, Lâm Đồng"
        },
        "ai_flag": {
            "confidence_score": 5.0,
            "risk_level": "safe",
            "status": "approved"
        },
        "scores": [
            {
                "criteria_id": 1,
                "criteria_name": "Bố cục & Ánh sáng",
                "score_value": 92.0,
                "max_score": 100,
                "comment": "Ánh sáng tự nhiên rất đẹp"
            }
        ],
        "feedbacks": [
            {
                "summary_feedback": "Tác phẩm xuất sắc, thể hiện rõ chất màu film Portra.",
                "final_recommendation": "Đề xuất giải Nhì"
            }
        ]
    }

    with patch.object(submission_controller_module.submission_service, 'get_submission_detail', return_value=mock_detail):
        response = client.get(
            '/submissions/101',
            headers={'Authorization': f'Bearer {token}'}
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data['id'] == 101
    assert data['film_metadata']['film_stock'] == 'Kodak Portra 400'
    assert data['final_score'] == 91.5
    assert len(data['scores']) == 1
    assert len(data['feedbacks']) == 1


def test_get_submission_detail_forbidden_for_other_user():
    """Test Participant is blocked from viewing another participant's submission details."""
    app = create_app()
    client = app.test_client()
    secret = app.config.get('SECRET_KEY', 'dev-secret-key-change-me-in-production-32chars')
    token = generate_jwt_token(secret, user_id=99, role='participant')

    with patch.object(
        submission_controller_module.submission_service,
        'get_submission_detail',
        side_effect=PermissionError("Access forbidden: You can only view your own submission details.")
    ):
        response = client.get(
            '/submissions/101',
            headers={'Authorization': f'Bearer {token}'}
        )

    assert response.status_code == 403
    data = response.get_json()
    assert "forbidden" in data['message'].lower()


def test_update_draft_submission_success():
    """Test Participant updating a draft submission successfully."""
    app = create_app()
    client = app.test_client()
    secret = app.config.get('SECRET_KEY', 'dev-secret-key-change-me-in-production-32chars')
    token = generate_jwt_token(secret, user_id=10, role='participant')

    mock_updated = MockSubObj(
        id=102,
        title="Phố Đêm Mưa - Hoàn Thiện",
        status="submitted",
        round_id=2,
        story_description="Đã bổ sung câu chuyện hoàn chỉnh",
        submitted_at=datetime(2026, 8, 19, 12, 0, 0),
        updated_at=datetime(2026, 8, 19, 12, 0, 0),
    )

    mock_svc = MagicMock()
    mock_svc.update_draft_submission.return_value = mock_updated
    mock_svc.update_draft.return_value = mock_updated
    patch_controller_attr('submission_service', mock_svc)

    response = client.put(
        '/submissions/102',
        headers={'Authorization': f'Bearer {token}'},
        json={
            "title": "Phố Đêm Mưa - Hoàn Thiện",
            "story_description": "Đã bổ sung câu chuyện hoàn chỉnh",
            "status": "submitted",
            "round_id": 2,
            "film_metadata": {
                "film_stock": "Kodak Tri-X 400",
                "camera_body": "Nikon FM2"
            }
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Submission updated successfully'
    assert data['submission']['title'] == 'Phố Đêm Mưa - Hoàn Thiện'
    assert data['submission']['status'] == 'submitted'


def test_update_non_draft_submission_rejected():
    """Test attempting to update an already submitted/graded submission is rejected."""
    app = create_app()
    client = app.test_client()
    secret = app.config.get('SECRET_KEY', 'dev-secret-key-change-me-in-production-32chars')
    token = generate_jwt_token(secret, user_id=10, role='participant')

    mock_svc = MagicMock()
    err = ValueError("Cannot edit submission with status 'submitted'. Only drafts can be modified.")
    mock_svc.update_draft_submission.side_effect = err
    mock_svc.update_draft.side_effect = err
    patch_controller_attr('submission_service', mock_svc)

    response = client.put(
        '/submissions/101',
        headers={'Authorization': f'Bearer {token}'},
        json={"title": "Trying to edit submitted"}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "only drafts can be modified" in data['message'].lower()


if __name__ == '__main__':
    test_get_my_submissions_success()
    test_get_submission_detail_authorized_owner()
    test_get_submission_detail_forbidden_for_other_user()
    test_update_draft_submission_success()
    test_update_non_draft_submission_rejected()
    print("All my_submissions tests passed successfully!")
