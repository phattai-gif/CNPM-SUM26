from flask import Blueprint, request, jsonify, current_app, render_template
from datetime import datetime, timedelta, timezone
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from api.schemas.auth import GoogleLoginRequestSchema

from infrastructure.models.app import UserModel, ContestModel, RoundModel
from api.schemas.auth import RegisterUserRequestSchema, RegisterUserResponseSchema, LoginUserRequestSchema, LoginUserResponseSchema
from api.role_required import token_required
from services.auth_service import AuthService
from infrastructure.repositories.auth_repository import AuthRepository
from infrastructure.repositories.contest_repository import ContestRepository
from services.contest_service import ContestService
from services.email_service import email_service
from urllib.parse import urlencode

PUBLIC_SIGNUP_ROLES = {'participant', 'organizer'}

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Khá»Ÿi táº¡o repository & service dÃ¹ng FactoryDatabase (PostgreSQL Supabase)
auth_service = AuthService(AuthRepository())
contest_service = ContestService(ContestRepository())

register_request_schema = RegisterUserRequestSchema()
register_response_schema = RegisterUserResponseSchema()
login_request_schema = LoginUserRequestSchema()
login_response_schema = LoginUserResponseSchema()
google_login_request_schema = GoogleLoginRequestSchema()


def _set_auth_cookie(response, token):
  response.set_cookie(
    'access_token',
    token,
    max_age=24 * 60 * 60,
    httponly=True,
    secure=False,
    samesite='Lax',
    path='/',
  )
  return response


def verify_google_token(id_token):
  """Verify Google's signed ID token and audience on the backend."""
  from google.auth.transport import requests as google_requests
  from google.oauth2 import id_token as google_id_token
  import os

  client_id = current_app.config.get('GOOGLE_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID')
  if not client_id:
    raise ValueError('Google OAuth is not configured.')
  claims = google_id_token.verify_oauth2_token(
    id_token,
    google_requests.Request(),
    client_id,
  )
  if claims.get('email_verified') is not True:
    raise ValueError('Google email is not verified.')
  return claims


@auth_bp.route('/google', methods=['POST'])
@auth_bp.route('/google-login', methods=['POST'])
def google_login():
    """
    Login or register user via Google Sign-In credentials/token.
    """
    import os
    data = request.get_json() or {}
    id_token_str = data.get('id_token') or data.get('credential')
    email = data.get('email')
    full_name = data.get('full_name') or data.get('name')
    avatar_url = data.get('avatar_url') or data.get('picture')

    if id_token_str:
        client_id = current_app.config.get('GOOGLE_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID')
        if client_id:
            try:
                claims = verify_google_token(id_token_str)
                email = claims.get('email') or email
                full_name = claims.get('name') or full_name
                avatar_url = claims.get('picture') or avatar_url
            except Exception:
                try:
                    claims = jwt.decode(id_token_str, options={"verify_signature": False})
                    email = claims.get('email') or email
                    full_name = claims.get('name') or full_name
                    avatar_url = claims.get('picture') or avatar_url
                except Exception:
                    pass
        else:
            try:
                claims = jwt.decode(id_token_str, options={"verify_signature": False})
                email = claims.get('email') or email
                full_name = claims.get('name') or full_name
                avatar_url = claims.get('picture') or avatar_url
            except Exception:
                pass

    if not email:
        return jsonify({'message': 'Email is required for Google Sign-In.'}), 400

    user = auth_service.login_google(email=email, full_name=full_name, avatar_url=avatar_url)
    if not user:
        return jsonify({'message': 'Could not authenticate Google user.'}), 500

    resp, status_code = _jwt_response(user)
    token_json = resp.get_json() if hasattr(resp, 'get_json') else {}
    if token_json and token_json.get('token'):
        _set_auth_cookie(resp, token_json['token'])
    return resp, status_code


def _jwt_response(user):
  payload = {
    'user_id': user.id,
    'username': user.username,
    'role': user.role,
    'exp': datetime.now(timezone.utc) + timedelta(hours=24)
  }
  secret_key = current_app.config.get('SECRET_KEY') or 'dev-secret-key-change-me-in-production-32chars'
  token = jwt.encode(payload, secret_key, algorithm='HS256')
  return jsonify({
    'message': 'Login successful!',
    'token': token,
    'user': {
      'id': user.id,
      'username': user.username,
      'email': user.email,
      'full_name': user.full_name,
      'role': user.role,
      'email_verified': getattr(user, 'email_verified', False)
    }
  }), 200

def _account_token(user_id, token_type, lifetime):
  secret_key = current_app.config.get('SECRET_KEY') or 'a_default_secret_key'
  return jwt.encode({
    'user_id': user_id,
    'type': token_type,
    'exp': datetime.now(timezone.utc) + lifetime
  }, secret_key, algorithm='HS256')


def _send_auth_token(email, token, path, subject, action_label, expires_in):
  base_url = current_app.config.get('BASE_URL', request.host_url.rstrip('/')).rstrip('/')
  action_url = f"{base_url}{path}?{urlencode({'token': token})}"
  return email_service.send_token_email(
    recipient=email,
    subject=subject,
    action_url=action_url,
    action_label=action_label,
    expires_in=expires_in,
  )


def _token_response_field(token, sent, field_name='token'):
  # Tokens remain available for local development/tests when SMTP is absent.
  if current_app.testing or not email_service.is_configured():
    return {field_name: token}
  return {}

@auth_bp.route('/check_router', methods=['GET'])
def check_router():
    """
    Check router health
    ---
    get:
      summary: Check router health
      tags:
        - Auth
      responses:
        200:
          description: Router is working
    """
    return jsonify({'message': 'Auth router is working!'}), 200


@auth_bp.route('/signup', methods=['POST'])
def register():
    """
    Register a new user with role
    ---
    post:
      summary: Register a new user (admin, organizer, participant, judge)
      tags:
        - Auth
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - username
                - email
                - password
                - passwordconfirm
              properties:
                username:
                  type: string
                  example: "john_photographer"
                email:
                  type: string
                  example: "john@example.com"
                password:
                  type: string
                  example: "password123"
                passwordconfirm:
                  type: string
                  example: "password123"
                full_name:
                  type: string
                  example: "John Doe"
                role:
                  type: string
                  enum: [admin, organizer, participant, judge]
                  default: participant
                  example: "participant"
      responses:
        201:
          description: User registered successfully
        400:
          description: Invalid input or user/email already exists
    """
    data = request.get_json() or {}

    errors = register_request_schema.validate(data)
    if errors:
        return jsonify({'message': 'Validation error', 'errors': errors}), 400

    username = data.get('username')
    email = (data.get('email') or '').strip().lower()
    password = data.get('password')
    passwordconfirm = data.get('passwordconfirm')
    full_name = data.get('full_name')
    role = data.get('role', 'participant').lower()

    if role not in PUBLIC_SIGNUP_ROLES:
        return jsonify({
            'message': 'Public registration only allows the participant role.'
        }), 403

    if password != passwordconfirm:
        return jsonify({'message': 'Passwords do not match'}), 400

    if auth_service.check_exist(username):
        return jsonify({'message': f'Username "{username}" already exists. Please choose another.'}), 400

    if auth_service.check_email_exist(email):
        return jsonify({'message': f'Email "{email}" is already registered.'}), 400

    # MÃ£ hÃ³a máº­t kháº©u
    password_hashed = generate_password_hash(password)

    new_user = auth_service.register(
        username=username,
        password=password_hashed,
        email=email,
        role=role,
        full_name=full_name
    )

    if not new_user:
        return jsonify({'message': 'Registration failed due to server error'}), 500

    verification_token = _account_token(
      new_user.id,
      'email_verification',
      timedelta(hours=24),
    )
    verification_sent = _send_auth_token(
      email,
      verification_token,
      '/auth/verify-email',
      'Verify your email address',
      'verify your email address',
      '24 hours',
    )

    # Auto-generate JWT token for newly registered user (auto-login)
    payload = {
      'user_id': new_user.id,
      'username': new_user.username,
      'role': new_user.role,
      'exp': datetime.utcnow() + timedelta(hours=24)
    }
    secret_key = current_app.config.get('SECRET_KEY') or 'a_default_secret_key'
    token = jwt.encode(payload, secret_key, algorithm='HS256')

    result = register_response_schema.dump(new_user)
    response = jsonify({
      'message': 'User registered successfully!',
      'token': token,
      'email_verification_required': True,
      'user': result
    })
    _set_auth_cookie(response, token)
    return response, 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user and get JWT Token with Role
    ---
    post:
      summary: Login user
      tags:
        - Auth
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - username
                - password
              properties:
                username:
                  type: string
                  example: "john_photographer"
                password:
                  type: string
                  example: "password123"
      responses:
        200:
          description: Successful login with JWT token and user role
        401:
          description: Invalid username or password
    """
    data = request.get_json() or {}

    errors = login_request_schema.validate(data)
    if errors:
        return jsonify({'message': 'Validation error', 'errors': errors}), 400

    username = data.get('username')
    password = data.get('password')

    user = auth_service.login(username, password)
    if not user:
        return jsonify({'message': 'Invalid username or password'}), 401

    # Táº¡o JWT Payload chá»©a thÃ´ng tin User ID, Username vÃ  Role
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24)
    }

    secret_key = current_app.config.get('SECRET_KEY') or 'dev-secret-key-change-me-in-production-32chars'
    token = jwt.encode(payload, secret_key, algorithm='HS256')

    response = jsonify({
        'message': 'Login successful!',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role
        }
    })
    _set_auth_cookie(response, token)
    return response, 200


@auth_bp.route('/login', methods=['GET'])
def login_page():
    import os
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID') or os.environ.get('GOOGLE_CLIENT_ID') or ''
    return render_template('login.html', google_client_id=google_client_id)


@auth_bp.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')


@auth_bp.route('/submit', methods=['GET'])
def submission_page():
    """Serve the submission form; protected APIs validate the stored JWT."""
    return render_template('submission.html')


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """
    Get current logged-in user profile
    ---
    get:
      summary: Get logged-in user profile from JWT token
      tags:
        - Auth
      security:
        - Bearer: []
      responses:
        200:
          description: User profile retrieved successfully
        401:
          description: Unauthorized
    """
    user_id = request.user.get('user_id')
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'email_verified': getattr(user, 'email_verified', False),
            'avatar_url': getattr(user, 'avatar_url', None),
            'bio': getattr(user, 'bio', None),
            'created_at': getattr(user, 'created_at', None)
        }
    }), 200


@auth_bp.route('/profile', methods=['PUT', 'PATCH'])
@token_required
def update_profile():
    return update_current_user()


@auth_bp.route('/me', methods=['PUT', 'PATCH'])
@token_required
def update_current_user():
    """
    Update logged-in user profile
    ---
    put:
      summary: Update user profile (full_name, bio, avatar_url)
      tags:
        - Auth
      security:
        - Bearer: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                full_name:
                  type: string
                bio:
                  type: string
                avatar_url:
                  type: string
      responses:
        200:
          description: Profile updated successfully
        400:
          description: Validation error
        401:
          description: Unauthorized
    """
    user_id = request.user.get('user_id')
    data = request.get_json(silent=True) or {}

    full_name = data.get('full_name')
    bio = data.get('bio')
    avatar_url = data.get('avatar_url')

    updated_user = auth_service.update_profile(
        user_id=user_id,
        full_name=full_name,
        bio=bio,
        avatar_url=avatar_url
    )

    if not updated_user:
        return jsonify({'message': 'Failed to update user profile'}), 400

    return jsonify({
        'message': 'Profile updated successfully',
        'user': {
            'id': updated_user.id,
            'username': updated_user.username,
            'email': updated_user.email,
            'full_name': updated_user.full_name,
            'role': updated_user.role,
            'avatar_url': updated_user.avatar_url,
            'bio': updated_user.bio,
            'created_at': updated_user.created_at
        }
    }), 200


@auth_bp.route('/profile', methods=['GET'])
def profile_page():
    """Serve the user profile and portfolio page"""
    return render_template('profile.html')


@auth_bp.route('/contests', methods=['GET'])
@token_required
def get_active_contests():
    """
    Get list of active contests for participants to submit to
    ---
    get:
      summary: Get active contests for submission
      tags:
        - Auth
      security:
        - Bearer: []
      responses:
        200:
          description: List of active contests retrieved successfully
        401:
          description: Unauthorized
    """
    try:
        allowed_contest_statuses = {
            'active',
            'ongoing',
            'published',
            'open',
        }
        allowed_round_statuses = {
            'active',
            'ongoing',
            'open',
            'published',
            'submission_open',
            'upcoming',
        }

        session = contest_service.repository.session
        all_contests = (
            session.query(ContestModel)
            .order_by(ContestModel.created_at.desc())
            .all()
        )

        active_contests = []
        for contest in all_contests:
            contest_status = str(getattr(contest, 'status', '') or '').lower()
            if contest_status not in allowed_contest_statuses:
                continue

            contest_dict = {
                'id': contest.id,
                'name': getattr(contest, 'name', '') or getattr(contest, 'title', ''),
                'title': getattr(contest, 'title', ''),
                'description': getattr(contest, 'description', ''),
                'status': getattr(contest, 'status', ''),
                'rounds': [],
            }

            round_models = (
                session.query(RoundModel)
                .filter_by(contest_id=contest.id)
                .order_by(RoundModel.round_number.asc())
                .all()
            )

            rounds = []
            for round_obj in round_models:
                round_status = str(getattr(round_obj, 'status', '') or '').lower()
                if round_status and round_status not in allowed_round_statuses:
                    continue

                rounds.append({
                    'id': round_obj.id,
                    'name': getattr(round_obj, 'title', None) or getattr(round_obj, 'name', None) or f'Round {getattr(round_obj, "round_number", "")}',
                    'title': getattr(round_obj, 'title', None) or getattr(round_obj, 'name', None) or f'Round {getattr(round_obj, "round_number", "")}',
                    'round_number': getattr(round_obj, 'round_number', None),
                    'deadline': getattr(round_obj, 'end_date', None).isoformat() if getattr(round_obj, 'end_date', None) else None,
                    'description': getattr(round_obj, 'description', ''),
                    'status': getattr(round_obj, 'status', ''),
                })

            contest_dict['rounds'] = rounds
            if rounds:
                active_contests.append(contest_dict)
        
        return jsonify({
            'message': 'Active contests retrieved successfully',
            'contests': active_contests
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Error retrieving contests',
            'error': str(e)
        }), 500


# ============================================================
# FORGOT PASSWORD & EMAIL VERIFICATION
# ============================================================

@auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    """Render the Forgot Password page."""
    return render_template('forgot_password.html')


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request a password reset link/token
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()

    if not email:
        return jsonify({'message': 'Email is required'}), 400

    user = auth_service.get_user_by_email(email)
    if not user:
        return jsonify({'message': 'Email does not exist'}), 404

    secret_key = current_app.config.get('SECRET_KEY', 'a_default_secret_key')
    payload = {
        'reset_email': email,
        'user_id': user.id,
        'type': 'password_reset',
        'exp': datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    reset_token = jwt.encode(payload, secret_key, algorithm='HS256')
    reset_sent = _send_auth_token(
      email,
      reset_token,
      '/auth/reset-password',
      'Reset your password',
      'reset your password',
      '15 minutes',
    )

    response = {
      'message': 'If the email is registered, a password reset link has been sent.'
    }
    response.update(_token_response_field(reset_token, reset_sent))
    return jsonify(response), 200


@auth_bp.route('/reset-password', methods=['GET'])
def reset_password_page():
    """Render the Reset Password page."""
    token = request.args.get('token', '')
    return render_template('reset_password.html', token=token)


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Reset password using a reset token
    """
    data = request.get_json() or {}
    token = data.get('token')
    password = data.get('password')
    passwordconfirm = data.get('passwordconfirm')

    if not token or not password or not passwordconfirm:
        return jsonify({'message': 'All fields are required'}), 400

    if password != passwordconfirm:
        return jsonify({'message': 'Passwords do not match'}), 400

    secret_key = current_app.config.get('SECRET_KEY', 'a_default_secret_key')
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        if payload.get('type') != 'password_reset':
            return jsonify({'message': 'Invalid token type'}), 400
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired'}), 400
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid token'}), 400

    user_id = payload.get('user_id')
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    password_hashed = generate_password_hash(password)
    success = auth_service.update_password(user.id, password_hashed)

    if not success:
        return jsonify({'message': 'Failed to reset password'}), 500

    return jsonify({'message': 'Password reset successful'}), 200


@auth_bp.route('/verify-email', methods=['GET'])
def verify_email_page():
    """Render the Email Verification page."""
    token = request.args.get('token', '')
    return render_template('verify_email.html', token=token)


@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """
    Verify user email using a token
    """
    data = request.get_json() or {}
    token = data.get('token')

    if not token:
        return jsonify({'message': 'Verification token is required'}), 400

    secret_key = current_app.config.get('SECRET_KEY', 'a_default_secret_key')
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        if payload.get('type') != 'email_verification':
            return jsonify({'message': 'Invalid token type'}), 400
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Verification token has expired'}), 400
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid verification token'}), 400

    user_id = payload.get('user_id')
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    success = (
        auth_service.update_email_verified(user.id, True)
        and auth_service.update_status(user.id, 'active')
    )
    if not success:
        return jsonify({'message': 'Failed to verify email'}), 500

    return jsonify({'message': 'Email verified successfully'}), 200


@auth_bp.route('/request-verification', methods=['POST'])
def request_verification():
    """
    Request a new email verification token
    """
    data = request.get_json() or {}
    email = data.get('email')

    if not email:
        return jsonify({'message': 'Email is required'}), 400

    user = auth_service.get_user_by_email(email)
    if not user:
        return jsonify({'message': 'Email does not exist'}), 404

    secret_key = current_app.config.get('SECRET_KEY', 'a_default_secret_key')
    payload = {
        'verify_email': email,
        'user_id': user.id,
        'type': 'email_verification',
        'exp': datetime.now(timezone.utc) + timedelta(days=1)
    }
    verify_token = jwt.encode(payload, secret_key, algorithm='HS256')
    verification_sent = _send_auth_token(
      email,
      verify_token,
      '/auth/verify-email',
      'Verify your email address',
      'verify your email address',
      '24 hours',
    )

    response = {'message': 'A verification link has been sent to your email.'}
    response.update(_token_response_field(verify_token, verification_sent))
    return jsonify(response), 200
