import os
import sys
import random
import string
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import jwt
from datetime import datetime, timedelta, timezone
from app import create_app
import api.controllers.submission_controller as submission_controller_module


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

    with patch('api.controllers.submission_controller.submission_repo.get_by_id_with_details', return_value=(mock_submission, mock_file, mock_film_metadata)):
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

    with patch('api.controllers.submission_controller.submission_repo.get_by_id_with_details', return_value=None):
        response = client.get(
            '/submissions/999',
            headers={'Authorization': f'Bearer {token}'}
        )

    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data['message'] == 'Submission not found'


if __name__ == '__main__':
    test_get_submission_details_success()
    test_get_submission_details_not_found()
    print('Submission detail tests passed')
