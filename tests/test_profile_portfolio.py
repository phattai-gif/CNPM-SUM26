import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app
from domain.models.auth import Auth


def generate_jwt_token(secret_key, user_id=1, username='film_photographer', role='participant'):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=2)
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client, app


def test_get_profile_ui(client):
    """Test accessing Profile & Portfolio page."""
    c, app = client
    res = c.get('/profile')
    assert res.status_code == 200
    assert b"Portfolio & H\xc3\xb4\xcc\x80 S\xc6\xa1" in res.data or b"Portfolio" in res.data


def test_get_portfolio_redirect_or_render(client):
    """Test /portfolio alias route."""
    c, app = client
    res = c.get('/portfolio')
    assert res.status_code in [200, 302]


def test_get_current_user_profile_with_bio_and_avatar(client):
    """Test GET /auth/me returns bio and avatar_url."""
    c, app = client
    secret = app.config.get('SECRET_KEY', 'dev-secret-key-change-me-in-production-32chars')
    token = generate_jwt_token(secret, user_id=42, username='leica_lover', role='participant')

    mock_user = Auth(
        id=42,
        username='leica_lover',
        email='leica@analog.club',
        password='hashed_password',
        passwordcomfirm='hashed_password',
        full_name='Nguyen Van Film',
        role='participant',
        avatar_url='https://images.unsplash.com/photo-1534528741775-53994a69daeb',
        bio='Đam mê nhiếp ảnh đường phố và tráng phim đen trắng.',
        created_at='2026-01-01T10:00:00'
    )

    with patch('api.controllers.auth_controller.auth_service.get_user_by_id', return_value=mock_user):
        res = c.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
        assert res.status_code == 200
        data = res.get_json()
        assert data['user']['username'] == 'leica_lover'
        assert data['user']['full_name'] == 'Nguyen Van Film'
        assert data['user']['avatar_url'] == 'https://images.unsplash.com/photo-1534528741775-53994a69daeb'
        assert 'đen trắng' in data['user']['bio']


def test_update_user_profile_success(client):
    """Test PUT /auth/profile updates profile data."""
    c, app = client
    secret = app.config.get('SECRET_KEY', 'dev-secret-key-change-me-in-production-32chars')
    token = generate_jwt_token(secret, user_id=42, username='leica_lover', role='participant')

    updated_mock_user = Auth(
        id=42,
        username='leica_lover',
        email='leica@analog.club',
        password='hashed_password',
        passwordcomfirm='hashed_password',
        full_name='Nguyen Van Film (Updated)',
        role='participant',
        avatar_url='https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d',
        bio='Cập nhật tiểu sử mới.',
        created_at='2026-01-01T10:00:00'
    )

    with patch('api.controllers.auth_controller.auth_service.update_profile', return_value=updated_mock_user):
        res = c.put(
            '/auth/profile',
            headers={'Authorization': f'Bearer {token}'},
            json={
                'full_name': 'Nguyen Van Film (Updated)',
                'bio': 'Cập nhật tiểu sử mới.',
                'avatar_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d'
            }
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data['message'] == 'Profile updated successfully'
        assert data['user']['full_name'] == 'Nguyen Van Film (Updated)'
        assert data['user']['bio'] == 'Cập nhật tiểu sử mới.'


def test_update_profile_unauthorized(client):
    """Test updating profile without token fails."""
    c, app = client
    res = c.put('/auth/profile', json={'bio': 'Hacker'})
    assert res.status_code == 401
