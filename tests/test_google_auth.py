import os
import sys
from types import SimpleNamespace

import jwt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app
from api.controllers import auth_controller


def test_google_login_requires_a_credential():
    app = create_app()
    response = app.test_client().post('/auth/google', json={})

    assert response.status_code == 400
    assert response.get_json()['message'] == 'Google ID token is required.'


def test_google_login_issues_the_same_jwt_session(monkeypatch):
    app = create_app()
    app.config['GOOGLE_CLIENT_ID'] = 'test-client-id'
    user = SimpleNamespace(
        id=17,
        username='google.user',
        email='google.user@example.com',
        full_name='Google User',
        role='participant',
    )

    monkeypatch.setattr(auth_controller, 'verify_google_token', lambda token: {
        'email': 'Google.User@example.com',
        'email_verified': True,
        'name': 'Google User',
        'picture': 'https://example.com/avatar.png',
    })
    monkeypatch.setattr(auth_controller.auth_service, 'login_google', lambda **kwargs: user)

    response = app.test_client().post('/auth/google', json={'credential': 'signed-google-token'})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload['user']['role'] == 'participant'
    decoded = jwt.decode(payload['token'], app.config['SECRET_KEY'], algorithms=['HS256'])
    assert decoded['user_id'] == user.id
    assert decoded['role'] == user.role