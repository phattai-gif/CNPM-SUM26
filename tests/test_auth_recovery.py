import sys
import os
import random
import string
import jwt
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app
from infrastructure.repositories.auth_repository import AuthRepository
from infrastructure.models.app import UserModel

def generate_random_user():
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return {
        "username": f"recovery_{rand_str}",
        "email": f"recovery_{rand_str}@example.com",
        "password": "password123",
        "passwordconfirm": "password123",
        "full_name": f"Recovery User {rand_str}",
        "role": "participant"
    }

def test_auth_recovery_and_verification_flow():
    app = create_app()
    client = app.test_client()
    repo = AuthRepository()

    # 1. Register a test user
    user_data = generate_random_user()
    res = client.post('/auth/signup', json=user_data)
    assert res.status_code == 201
    
    # Check that user is active by default
    user_obj = repo.session.query(UserModel).filter_by(email=user_data['email']).first()
    assert user_obj is not None
    assert user_obj.status == 'active'
    assert user_obj.email_verified is False
    assert 'verification_token' in res.get_json()

    # 2. Test GET pages (render templates)
    res = client.get('/auth/forgot-password')
    assert res.status_code == 200
    assert b"Forgot Password" in res.data

    res = client.get('/auth/reset-password')
    assert res.status_code == 200
    assert b"Reset Password" in res.data

    res = client.get('/auth/verify-email')
    assert res.status_code == 200
    assert b"Verify Email" in res.data

    # 3. Test POST /auth/forgot-password with invalid email
    res = client.post('/auth/forgot-password', json={"email": "non_existent@example.com"})
    assert res.status_code == 404
    assert res.get_json()['message'] == 'Email does not exist'

    # 4. Test POST /auth/forgot-password with valid email
    res = client.post('/auth/forgot-password', json={"email": user_data['email']})
    assert res.status_code == 200
    res_json = res.get_json()
    assert 'token' in res_json
    reset_token = res_json['token']

    # 5. Test POST /auth/reset-password validation
    # - Mismatching passwords
    res = client.post('/auth/reset-password', json={
        "token": reset_token,
        "password": "newpassword123",
        "passwordconfirm": "mismatchpassword"
    })
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Passwords do not match'

    # - Invalid token
    res = client.post('/auth/reset-password', json={
        "token": "invalid.jwt.token",
        "password": "newpassword123",
        "passwordconfirm": "newpassword123"
    })
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Invalid token'

    # - Expired token
    secret_key = app.config.get('SECRET_KEY', 'a_default_secret_key')
    expired_payload = {
        'reset_email': user_data['email'],
        'user_id': user_obj.id,
        'type': 'password_reset',
        'exp': datetime.now(timezone.utc) - timedelta(minutes=5)
    }
    expired_token = jwt.encode(expired_payload, secret_key, algorithm='HS256')
    res = client.post('/auth/reset-password', json={
        "token": expired_token,
        "password": "newpassword123",
        "passwordconfirm": "newpassword123"
    })
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Token has expired'

    # - Valid password reset
    res = client.post('/auth/reset-password', json={
        "token": reset_token,
        "password": "newpassword123",
        "passwordconfirm": "newpassword123"
    })
    assert res.status_code == 200
    assert res.get_json()['message'] == 'Password reset successful'

    # - Verify we can login with the new password
    res = client.post('/auth/login', json={
        "username": user_data['username'],
        "password": "newpassword123"
    })
    assert res.status_code == 200
    assert 'token' in res.get_json()

    # 6. Test Email Verification Flow
    # - Manually set user status to pending
    repo.update_status(user_obj.id, 'pending')
    repo.session.refresh(user_obj)
    assert user_obj.status == 'pending'

    # - Try logging in (should fail because status is not active)
    res = client.post('/auth/login', json={
        "username": user_data['username'],
        "password": "newpassword123"
    })
    assert res.status_code == 401

    # - Request a verification token
    res = client.post('/auth/request-verification', json={"email": user_data['email']})
    assert res.status_code == 200
    verify_token = res.get_json()['token']

    # - Verify email with invalid token
    res = client.post('/auth/verify-email', json={"token": "invalid.verification.token"})
    assert res.status_code == 400

    # - Verify email with valid token
    res = client.post('/auth/verify-email', json={"token": verify_token})
    assert res.status_code == 200
    assert res.get_json()['message'] == 'Email verified successfully'

    # - User status should now be active
    repo.session.refresh(user_obj)
    assert user_obj.status == 'active'
    assert user_obj.email_verified is True

    # - Login should succeed now
    res = client.post('/auth/login', json={
        "username": user_data['username'],
        "password": "newpassword123"
    })
    assert res.status_code == 200

if __name__ == '__main__':
    test_auth_recovery_and_verification_flow()
