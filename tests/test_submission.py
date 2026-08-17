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

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_submission, mock_file, mock_film_metadata)
    mock_repo.get_ai_flag.return_value = None
    patch_controller_attr('submission_repo', mock_repo)

    response = client.get(
        '/submissions/123',
        headers={'Authorization': f'Bearer {token}'}
    )

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
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'))

    img1 = create_sample_image(width=100, height=100, color=(255, 0, 0))
    img2 = create_sample_image(width=200, height=200, color=(0, 255, 0))
    img3 = create_sample_image(width=300, height=300, color=(0, 0, 255))

    mock_submission = MockObject(
        id=77,
        round_id=2,
        user_id=1,
        title="Multi Image Entry",
        story_description="Series of photos",
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
        'round_id': '2',
        'title': 'Multi Image Entry',
        'film_stock': 'Fuji C200',
        'file1': (io.BytesIO(img1), 'image1.jpg', 'image/jpeg'),
        'file2': (io.BytesIO(img2), 'image2.jpg', 'image/jpeg'),
        'file3': (io.BytesIO(img3), 'image3.jpg', 'image/jpeg'),
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 201
    assert mock_repo.create_submission.called
    kwargs = mock_repo.create_submission.call_args[1]
    assert len(kwargs['files_data']) == 3
    hashes = [f['file_hash'] for f in kwargs['files_data']]
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
    }

    res = client.post(
        '/submissions',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert res.status_code == 400
    res_data = res.get_json()
    assert 'No image file provided' in res_data['message']


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


# Test 6 — Transaction rollback simulation
def test_post_submission_transaction_rollback():
    mock_session = MagicMock()

    def mock_add(obj):
        if obj.__class__.__name__ == 'SubmissionFilmMetadataModel':
            raise RuntimeError("Database constraint failure during metadata creation")

    mock_session.add.side_effect = mock_add

    repo = SubmissionRepository(session=mock_session)
    mock_session.query.return_value.filter_by.return_value.first.return_value = MockObject(id=1)

    try:
        repo.create_submission(
            round_id=1,
            user_id=1,
            title="Rollback Test",
            files_data=[{
                "image_hd_url": "https://example.com/test.jpg",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "file_hash": "hash123",
            }],
            film_stock="Kodak Portra 400",
        )
        assert False, "Should raise RuntimeError"
    except RuntimeError as e:
        assert "Database constraint failure" in str(e)

    assert mock_session.rollback.called


if __name__ == '__main__':
    test_get_submission_details_success()
    test_get_submission_details_not_found()
    print('Submission detail tests passed')
