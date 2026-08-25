import os
import sys
import io
import hashlib
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import jwt
from PIL import Image
from app import create_app

import src.api.controllers.submission_controller as submission_controller_module
try:
    import api.controllers.submission_controller as alt_submission_controller_module
except ImportError:
    alt_submission_controller_module = submission_controller_module

from services.submission_service import SubmissionService
from infrastructure.repositories.submission_repository import SubmissionRepository
from infrastructure.services.storage.local_storage_adapter import LocalStorageAdapter
from services.storage_service import StorageService


def patch_controller_attr(attr_name, value):
    for mod_name in ['src.api.controllers.submission_controller', 'api.controllers.submission_controller']:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            setattr(mod, attr_name, value)
            if attr_name == 'submission_repo':
                mod.submission_service = SubmissionService(submission_repo=value)


def generate_token(secret_key, user_id=1, username='testuser', role='organizer'):
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


class MockObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def create_sample_image(width=200, height=150, color=(255, 0, 0), format_name="JPEG"):
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def test_get_submission_details_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    mock_submission = MockObject(
        id=123,
        round_id=10,
        user_id=5,
        title='Test Submission',
        story_description='A sample story',
        status='submitted',
        final_score=8.75,
        submitted_at=datetime(2024, 1, 1, 12, 0, 0),
        created_at=datetime(2024, 1, 1, 11, 0, 0),
        updated_at=datetime(2024, 1, 1, 11, 30, 0),
    )
    mock_file = MockObject(
        id=1,
        image_hd_url='https://example.com/image.png',
        thumbnail_url='https://example.com/thumb.png',
        width_px=2048,
        height_px=1536,
        file_size_bytes=123456,
        file_hash='abc123',
        created_at=datetime(2024, 1, 1, 11, 0, 1),
    )
    mock_film_metadata = MockObject(
        film_stock='Kodak Portra 400',
        film_iso=400,
        camera_body='Leica M6',
        lens='50mm f/1.4',
        lab_name='Zone5',
        scanner_info='Fuji Frontier',
        development_process='C-41',
        taken_at_location='Hanoi',
        created_at=datetime(2024, 1, 1, 11, 0, 2),
    )

    mock_svc = MagicMock()
    mock_svc.get_submission_detail.return_value = None
    mock_svc.get_submission_by_id.return_value = (mock_submission, mock_file, mock_film_metadata)
    patch_controller_attr('submission_service', mock_svc)

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_submission, mock_file, mock_film_metadata)
    mock_repo.get_ai_flag.return_value = None
    patch_controller_attr('submission_repo', mock_repo)

    response = client.get(
        '/submissions/123',
        headers={'Authorization': f'Bearer {token}'}
    )

    if response.status_code != 200:
        print(f"DEBUG status={response.status_code}, data={response.get_json()}")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['id'] == 123
    assert json_data['file']['image_hd_url'] == 'https://example.com/image.png'
    assert json_data['film_metadata']['film_stock'] == 'Kodak Portra 400'
    assert json_data['status'] == 'submitted'


def test_get_submission_details_not_found():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    mock_svc = MagicMock()
    mock_svc.get_submission_detail.return_value = None
    mock_svc.get_submission_by_id.return_value = None
    patch_controller_attr('submission_service', mock_svc)

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = None
    patch_controller_attr('submission_repo', mock_repo)

    response = client.get(
        '/submissions/999',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data['message'] == 'Submission not found'


# --------------------------------------------------------------------------
# Task: Refactor API nộp bài sang multipart upload - Required Test Cases
# --------------------------------------------------------------------------

# Test 1 — Upload thành công (multipart/form-data)
def test_post_submission_multipart_success(tmp_path):
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    img_bytes = create_sample_image(width=400, height=300)
    expected_hash = hashlib.sha256(img_bytes).hexdigest()

    mock_submission = MockObject(
        id=55,
        round_id=1,
        user_id=10,
        title="Sunset in Saigon",
        story_description="Beautiful golden hour photo",
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )

    adapter = LocalStorageAdapter(upload_folder=str(tmp_path), base_url="/static/uploads")
    storage_svc = StorageService(adapter=adapter)
    mock_repo = MagicMock()
    mock_repo.create_submission.return_value = mock_submission

    custom_svc = SubmissionService(submission_repo=mock_repo, storage_service=storage_svc)
    patch_controller_attr('submission_service', custom_svc)

    data = {
        'round_id': '1',
        'title': 'Sunset in Saigon',
        'description': 'Beautiful golden hour photo',
        'film_stock': 'Kodak Portra 400',
        'film_iso': '400',
        'camera_body': 'Leica M6',
        'file': (io.BytesIO(img_bytes), 'saigon.jpg', 'image/jpeg')
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data['message'] == 'Submission created successfully'
    assert res_data['submission']['id'] == 55
    assert res_data['submission']['title'] == 'Sunset in Saigon'

    assert mock_repo.create_submission.called
    kwargs = mock_repo.create_submission.call_args[1]
    assert kwargs['round_id'] == 1
    assert kwargs['user_id'] == 10
    assert kwargs['title'] == 'Sunset in Saigon'
    assert kwargs['film_stock'] == 'Kodak Portra 400'
    assert kwargs['files_data'][0]['file_hash'] == expected_hash
    assert '/static/uploads/' in kwargs['files_data'][0]['image_hd_url']


# Test 2 — Upload nhiều ảnh
def test_post_submission_multiple_images(tmp_path):
    app = create_app()
    client = app.test_client()

    token = generate_token(
        app.config.get(
            "SECRET_KEY",
            "a_default_secret_key",
        )
    )

    img1 = create_sample_image(
        width=100,
        height=100,
        color=(255, 0, 0),
    )

    img2 = create_sample_image(
        width=200,
        height=200,
        color=(0, 255, 0),
    )

    img3 = create_sample_image(
        width=300,
        height=300,
        color=(0, 0, 255),
    )

    mock_submission = MockObject(
        id=77,
        round_id=2,
        user_id=1,
        title="Multi Image Entry",
        story_description="Series of photos",
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )

    adapter = LocalStorageAdapter(
        upload_folder=str(tmp_path),
        base_url="/static/uploads",
    )

    storage_svc = StorageService(
        adapter=adapter,
    )

    mock_repo = MagicMock()

    mock_repo.create_submission.return_value = (
        mock_submission
    )

    custom_svc = SubmissionService(
        submission_repo=mock_repo,
        storage_service=storage_svc,
    )

    patch_controller_attr(
        "submission_service",
        custom_svc,
    )

    data = {
        "round_id": "2",
        "title": "Multi Image Entry",
        "film_stock": "Fuji C200",

        "main_image": (
            io.BytesIO(img1),
            "image1.jpg",
            "image/jpeg",
        ),

        "negative": [
            (
                io.BytesIO(img2),
                "image2.jpg",
                "image/jpeg",
            ),
            (
                io.BytesIO(img3),
                "image3.jpg",
                "image/jpeg",
            ),
        ],
    }

    res = client.post(
        "/submissions",
        data=data,
        content_type="multipart/form-data",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    print("STATUS CODE:", res.status_code)
    print("RESPONSE:", res.get_json())

    assert res.status_code == 201

    assert mock_repo.create_submission.called

    kwargs = (
        mock_repo
        .create_submission
        .call_args[1]
    )

    assert "files_data" in kwargs

    files_data = kwargs["files_data"]

    assert len(files_data) == 3

    file_types = [
        file_data["file_type"]
        for file_data in files_data
    ]

    assert file_types.count("main_image") == 1
    assert file_types.count("negative") == 2

    hashes = [
        file_data["file_hash"]
        for file_data in files_data
    ]

    assert len(hashes) == 3
    assert len(set(hashes)) == 3


# Test 3 — Client không gửi hash (Backend tự tính file_hash)
def test_post_submission_backend_generates_file_hash(tmp_path):
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    img_bytes = create_sample_image(width=150, height=150)
    expected_hash = hashlib.sha256(img_bytes).hexdigest()

    mock_submission = MockObject(
        id=88,
        round_id=1,
        user_id=1,
        title="No Hash Sent",
        story_description="",
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )

    adapter = LocalStorageAdapter(upload_folder=str(tmp_path), base_url="/static/uploads")
    storage_svc = StorageService(adapter=adapter)
    mock_repo = MagicMock()
    mock_repo.create_submission.return_value = mock_submission

    custom_svc = SubmissionService(submission_repo=mock_repo, storage_service=storage_svc)
    patch_controller_attr('submission_service', custom_svc)

    data = {
        'round_id': '1',
        'title': 'No Hash Sent',
        'film_stock': 'Kodak Gold 200',
        'file_hash': 'fake_client_hash_123',
        'file': (io.BytesIO(img_bytes), 'nohash.jpg', 'image/jpeg'),
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 201
    kwargs = mock_repo.create_submission.call_args[1]
    assert kwargs['files_data'][0]['file_hash'] == expected_hash
    assert kwargs['files_data'][0]['file_hash'] != 'fake_client_hash_123'


# Test 4 — Thiếu file
def test_post_submission_missing_file():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    data = {
        'round_id': '1',
        'title': 'Missing File Entry',
        'film_stock': 'Kodak Portra 400',
        'status': 'submitted',
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400
    res_data = res.get_json()
    assert (
        "main_image is required" in res_data["message"]
        or "No image file provided" in res_data["message"]
    )
# Test 5 — Round không tồn tại
def test_post_submission_round_not_exists(tmp_path):
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    img_bytes = create_sample_image()
    mock_repo = MagicMock()
    mock_repo.create_submission.side_effect = ValueError("Round with id 99999 does not exist")

    adapter = LocalStorageAdapter(upload_folder=str(tmp_path), base_url="/static/uploads")
    storage_svc = StorageService(adapter=adapter)
    custom_svc = SubmissionService(submission_repo=mock_repo, storage_service=storage_svc)
    patch_controller_attr('submission_service', custom_svc)

    data = {
        'round_id': '99999',
        'title': 'Invalid Round Entry',
        'film_stock': 'Kodak Portra 400',
        'file': (io.BytesIO(img_bytes), 'test.jpg', 'image/jpeg'),
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400
    res_data = res.get_json()
    assert 'Round with id 99999 does not exist' in res_data['message']


# --------------------------------------------------------------------------
# Task: Xây dựng API lưu nháp và gửi chính thức bài dự thi - Tests
# --------------------------------------------------------------------------

def test_create_draft_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_submission = MockObject(
        id=101,
        round_id=1,
        user_id=10,
        title="Draft Title",
        story_description="Draft Description",
        status="draft",
        submitted_at=None,
    )

    mock_repo = MagicMock()
    mock_repo.create_submission.return_value = mock_submission
    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    data = {
        'round_id': '1',
        'title': 'Draft Title',
        'description': 'Draft Description',
        'status': 'draft',
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data['submission']['status'] == 'draft'
    assert mock_repo.create_submission.called


def test_create_incomplete_draft_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_submission = MockObject(
        id=102,
        round_id=1,
        user_id=10,
        title="",
        story_description="",
        status="draft",
        submitted_at=None,
    )

    mock_repo = MagicMock()
    mock_repo.create_submission.return_value = mock_submission
    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    data = {
        'round_id': '1',
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data['submission']['status'] == 'draft'


def test_update_draft_owner_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_submission = MockObject(
        id=101,
        round_id=1,
        user_id=10,
        title="Updated Draft Title",
        story_description="Updated Description",
        status="draft",
    )

    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = MockObject(id=101, user_id=10, status="draft")
    mock_repo.update_draft.return_value = mock_submission

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    data = {
        'title': 'Updated Draft Title',
        'description': 'Updated Description',
    }

    res = client.put(
        '/submissions/101',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 200
    res_data = res.get_json()
    assert res_data['submission']['title'] == 'Updated Draft Title'


def test_update_draft_other_user_forbidden():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=99)

    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = MockObject(id=101, user_id=10, status="draft")

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.put(
        '/submissions/101',
        data={'title': 'Hacker Update'},
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 403


def test_update_submission_submitted_error():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = MockObject(id=101, user_id=10, status="submitted")

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.put(
        '/submissions/101',
        data={'title': 'Try Update Submitted'},
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400


def test_update_submission_flagged_error():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = MockObject(id=101, user_id=10, status="flagged")

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.put(
        '/submissions/101',
        data={'title': 'Try Update Flagged'},
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400


def test_update_submission_evaluated_error():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = MockObject(id=101, user_id=10, status="evaluated")

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.put(
        '/submissions/101',
        data={'title': 'Try Update Evaluated'},
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400


def test_submit_draft_owner_success():
    app = create_app()
    app.config['TESTING'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
    client = app.test_client()
    token = generate_token(
        app.config.get('SECRET_KEY', 'a_default_secret_key'),
        user_id=10
    )

    mock_sub = MockObject(
        id=101,
        user_id=10,
        status="draft",
        title="Official Entry"
    )

    mock_file = MockObject(
        id=1,
        image_hd_url="https://example.com/hd.jpg"
    )

    mock_meta = MockObject(
        film_stock="Kodak Portra 400"
    )

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (
        mock_sub,
        mock_file,
        mock_meta
    )

    mock_repo.update_status.return_value = MockObject(
        id=101,
        status="submitted"
    )

    custom_svc = SubmissionService(
        submission_repo=mock_repo
    )

    patch_controller_attr(
        'submission_service',
        custom_svc
    )

    res = client.post(
        '/submissions/101/submit',
        headers={
            'Authorization': f'Bearer {token}'
        }
    )

    print("STATUS:", res.status_code)
    print("JSON:", res.get_json())
    assert res.status_code == 200
    res_data = res.get_json()

    assert res_data['message'] == "Submission submitted successfully"
    assert res_data['submission']['status'] == "submitted"
def test_submit_not_found():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = None

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.post(
        '/submissions/999/submit',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 404


def test_submit_other_user_forbidden():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=99)

    mock_sub = MockObject(id=101, user_id=10, status="draft", title="Official Entry")
    mock_file = MockObject(id=1, image_hd_url="https://example.com/hd.jpg")
    mock_meta = MockObject(film_stock="Kodak Portra 400")

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_sub, mock_file, mock_meta)

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.post(
        '/submissions/101/submit',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 403


def test_submit_already_submitted_error():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_sub = MockObject(id=101, user_id=10, status="submitted", title="Official Entry")
    mock_file = MockObject(id=1, image_hd_url="https://example.com/hd.jpg")
    mock_meta = MockObject(film_stock="Kodak Portra 400")

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_sub, mock_file, mock_meta)

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.post(
        '/submissions/101/submit',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400


def test_submit_flagged_error():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_sub = MockObject(id=101, user_id=10, status="flagged", title="Official Entry")
    mock_file = MockObject(id=1, image_hd_url="https://example.com/hd.jpg")
    mock_meta = MockObject(film_stock="Kodak Portra 400")

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_sub, mock_file, mock_meta)

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.post(
        '/submissions/101/submit',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400


def test_submit_evaluated_error():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_sub = MockObject(id=101, user_id=10, status="evaluated", title="Official Entry")
    mock_file = MockObject(id=1, image_hd_url="https://example.com/hd.jpg")
    mock_meta = MockObject(film_stock="Kodak Portra 400")

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_sub, mock_file, mock_meta)

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.post(
        '/submissions/101/submit',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400


def test_submit_missing_required_data_error():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_sub = MockObject(id=101, user_id=10, status="draft", title="")
    mock_file = MockObject(id=1, image_hd_url="https://example.com/hd.jpg")
    mock_meta = MockObject(film_stock="Kodak Portra 400")

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_sub, mock_file, mock_meta)

    custom_svc = SubmissionService(submission_repo=mock_repo)
    patch_controller_attr('submission_service', custom_svc)

    res = client.post(
        '/submissions/101/submit',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400


    assert res.status_code == 400


# ==============================================================================
# Task: Role-based Submission List APIs (25 Required Test Cases)
# ==============================================================================

# PARTICIPANT TESTS (1-6)

def test_1_participant_get_own_submissions():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    mock_svc = MagicMock()
    mock_svc.get_my_submissions.return_value = {
        "submissions": [{"id": 1, "user_id": 10, "title": "My Photo"}],
        "total": 1
    }
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/submissions/my', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['total'] == 1
    assert data['submissions'][0]['user_id'] == 10
    mock_svc.get_my_submissions.assert_called_with(user_id=10, round_id=None, status=None, ai_flag=None)


def test_2_participant_cannot_get_others_submissions():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    mock_svc = MagicMock()
    mock_svc.get_my_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/submissions/my?user_id=99', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_my_submissions.assert_called_with(user_id=10, round_id=None, status=None, ai_flag=None)


def test_3_participant_filter_round():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    mock_svc = MagicMock()
    mock_svc.get_my_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/submissions/my?round_id=2', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_my_submissions.assert_called_with(user_id=10, round_id=2, status=None, ai_flag=None)


def test_4_participant_filter_status():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    mock_svc = MagicMock()
    mock_svc.get_my_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/submissions/my?status=submitted', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_my_submissions.assert_called_with(user_id=10, round_id=None, status='submitted', ai_flag=None)


def test_5_participant_filter_ai_flag():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    mock_svc = MagicMock()
    mock_svc.get_my_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/submissions/my?ai_flag=high', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_my_submissions.assert_called_with(user_id=10, round_id=None, status=None, ai_flag='high')


def test_6_participant_empty_submissions():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    mock_svc = MagicMock()
    mock_svc.get_my_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/submissions/my', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['submissions'] == []
    assert data['total'] == 0


# ORGANIZER TESTS (7-11)

def test_7_organizer_get_contest_submissions_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=5, role='organizer')

    mock_svc = MagicMock()
    mock_svc.get_organizer_submissions.return_value = {
        "submissions": [{"id": 10, "title": "Contest Entry"}],
        "total": 1
    }
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/organizer/contests/1/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['total'] == 1


def test_8_organizer_cannot_get_other_contest_submissions():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=5, role='organizer')

    mock_svc = MagicMock()
    mock_svc.get_organizer_submissions.side_effect = PermissionError("Forbidden")
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/organizer/contests/99/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


def test_9_organizer_filter_round():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=5, role='organizer')

    mock_svc = MagicMock()
    mock_svc.get_organizer_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/organizer/contests/1/submissions?round_id=2', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_organizer_submissions.assert_called_with(
        contest_id=1, user_id=5, user_role='organizer', round_id=2, status=None, ai_flag=None
    )


def test_10_organizer_filter_status():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=5, role='organizer')

    mock_svc = MagicMock()
    mock_svc.get_organizer_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/organizer/contests/1/submissions?status=submitted', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_organizer_submissions.assert_called_with(
        contest_id=1, user_id=5, user_role='organizer', round_id=None, status='submitted', ai_flag=None
    )


def test_11_organizer_filter_ai_flag():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=5, role='organizer')

    mock_svc = MagicMock()
    mock_svc.get_organizer_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/organizer/contests/1/submissions?ai_flag=high', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_organizer_submissions.assert_called_with(
        contest_id=1, user_id=5, user_role='organizer', round_id=None, status=None, ai_flag='high'
    )


# JUDGE TESTS (12-17)

def test_12_judge_get_assignment_submissions_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=7, role='judge')

    mock_svc = MagicMock()
    mock_svc.get_judge_assignment_submissions.return_value = {
        "submissions": [{"id": 20, "title": "Assigned Photo"}],
        "total": 1
    }
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/judge/assignments/1/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['total'] == 1


def test_13_judge_cannot_get_other_assignment_submissions():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=7, role='judge')

    mock_svc = MagicMock()
    mock_svc.get_judge_assignment_submissions.side_effect = PermissionError("Forbidden")
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/judge/assignments/99/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


def test_14_judge_cannot_use_other_judge_id_for_assignment():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=7, role='judge')

    mock_svc = MagicMock()
    mock_svc.get_judge_assignment_submissions.side_effect = PermissionError("Forbidden")
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/judge/assignments/2/submissions?judge_id=88', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403
    mock_svc.get_judge_assignment_submissions.assert_called_with(
        assignment_id=2, user_id=7, user_role='judge', round_id=None, status=None, ai_flag=None
    )


def test_15_judge_filter_round():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=7, role='judge')

    mock_svc = MagicMock()
    mock_svc.get_judge_assignment_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/judge/assignments/1/submissions?round_id=2', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_judge_assignment_submissions.assert_called_with(
        assignment_id=1, user_id=7, user_role='judge', round_id=2, status=None, ai_flag=None
    )


def test_16_judge_filter_status():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=7, role='judge')

    mock_svc = MagicMock()
    mock_svc.get_judge_assignment_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/judge/assignments/1/submissions?status=submitted', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_judge_assignment_submissions.assert_called_with(
        assignment_id=1, user_id=7, user_role='judge', round_id=None, status='submitted', ai_flag=None
    )


def test_17_judge_filter_ai_flag():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=7, role='judge')

    mock_svc = MagicMock()
    mock_svc.get_judge_assignment_submissions.return_value = {"submissions": [], "total": 0}
    patch_controller_attr('submission_service', mock_svc)

    res = client.get('/judge/assignments/1/submissions?ai_flag=high', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    mock_svc.get_judge_assignment_submissions.assert_called_with(
        assignment_id=1, user_id=7, user_role='judge', round_id=None, status=None, ai_flag='high'
    )


# AUTH TESTS (18-22)

def test_18_no_token_unauthorized():
    app = create_app()
    client = app.test_client()

    res = client.get('/submissions/my')
    assert res.status_code == 401

    res = client.get('/organizer/contests/1/submissions')
    assert res.status_code == 401

    res = client.get('/judge/assignments/1/submissions')
    assert res.status_code == 401


def test_19_participant_cannot_call_organizer_api():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    res = client.get('/organizer/contests/1/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


def test_20_participant_cannot_call_judge_api():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    res = client.get('/judge/assignments/1/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


def test_21_judge_cannot_call_organizer_api():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=7, role='judge')

    res = client.get('/organizer/contests/1/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


def test_22_organizer_cannot_call_judge_api():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=5, role='organizer')

    res = client.get('/judge/assignments/1/submissions', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 403


# VALIDATION TESTS (23-25)

def test_23_invalid_round_id():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    res = client.get('/submissions/my?round_id=invalid_id', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Invalid round_id'


def test_24_invalid_status():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    res = client.get('/submissions/my?status=unknown_status', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Invalid status'


def test_25_invalid_ai_flag():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='participant')

    res = client.get('/submissions/my?ai_flag=ultra_high', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Invalid ai_flag'


if __name__ == '__main__':
    test_get_submission_details_success()
    test_get_submission_details_not_found()
    print('Submission detail tests passed')


