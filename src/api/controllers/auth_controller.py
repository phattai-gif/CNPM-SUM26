from flask import Blueprint, request, jsonify, current_app, render_template
from datetime import datetime, timedelta, timezone
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

from infrastructure.models.app import UserModel
from infrastructure.databases.mssql import session
from api.schemas.auth import RegisterUserRequestSchema, RegisterUserResponseSchema, LoginUserRequestSchema, LoginUserResponseSchema
from api.role_required import token_required
from services.auth_service import AuthService
from infrastructure.repositories.auth_repository import AuthRepository
from infrastructure.repositories.contest_repository import ContestRepository
from services.contest_service import ContestService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Khởi tạo repository & service dùng FactoryDatabase (PostgreSQL Supabase)
auth_service = AuthService(AuthRepository())
contest_service = ContestService(ContestRepository())

register_request_schema = RegisterUserRequestSchema()
register_response_schema = RegisterUserResponseSchema()
login_request_schema = LoginUserRequestSchema()
login_response_schema = LoginUserResponseSchema()


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
    email = data.get('email')
    password = data.get('password')
    passwordconfirm = data.get('passwordconfirm')
    full_name = data.get('full_name')
    role = data.get('role', 'participant').lower()

    if password != passwordconfirm:
        return jsonify({'message': 'Passwords do not match'}), 400

    if auth_service.check_exist(username):
        return jsonify({'message': f'Username "{username}" already exists. Please choose another.'}), 400

    if auth_service.check_email_exist(email):
        return jsonify({'message': f'Email "{email}" is already registered.'}), 400

    # Mã hóa mật khẩu
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

    result = register_response_schema.dump(new_user)
    return jsonify({
        'message': 'User registered successfully!',
        'user': result
    }), 201


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

    # Tạo JWT Payload chứa thông tin User ID, Username và Role
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
            'role': user.role
        }
    }), 200


@auth_bp.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')


@auth_bp.route('/submit', methods=['GET'])
@token_required
def submission_page():
    """Serve the submission form page for participants"""
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
            'role': user.role
        }
    }), 200


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
        # Get all contests
        all_contests = contest_service.get_all_contests()
        
        # Filter to only active contests with rounds
        active_contests = []
        for contest in all_contests:
            if hasattr(contest, 'status') and contest.status in ['active', 'ongoing']:
                contest_dict = contest.to_dict() if hasattr(contest, 'to_dict') else {
                    'id': contest.id,
                    'name': getattr(contest, 'name', ''),
                    'title': getattr(contest, 'title', ''),
                    'description': getattr(contest, 'description', ''),
                    'status': getattr(contest, 'status', ''),
                }
                
                # Get rounds for this contest
                if hasattr(contest, 'rounds'):
                    rounds = []
                    for round_obj in contest.rounds:
                        round_dict = round_obj.to_dict() if hasattr(round_obj, 'to_dict') else {
                            'id': round_obj.id,
                            'name': getattr(round_obj, 'name', ''),
                            'deadline': getattr(round_obj, 'deadline', ''),
                            'description': getattr(round_obj, 'description', ''),
                        }
                        rounds.append(round_dict)
                    contest_dict['rounds'] = rounds
                
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