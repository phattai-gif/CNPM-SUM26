from functools import wraps
from flask import request, jsonify, current_app
import jwt


def token_required(f):
    """Decorator kiểm tra JWT Token hợp lệ"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Lấy token từ Authorization Header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'message': 'Authorization token is missing!'}), 401

        try:
            secret_key = current_app.config.get('SECRET_KEY') or 'a_default_secret_key'
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            request.user = {
                'user_id': payload.get('user_id'),
                'username': payload.get('username'),
                'role': payload.get('role', 'participant')
            }
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired! Please login again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """Decorator kiểm tra JWT Token và xác thực Vai trò (Role) của người dùng"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            user_role = request.user.get('role')
            if allowed_roles and user_role not in allowed_roles:
                return jsonify({
                    'message': f'Access forbidden! Role "{user_role}" is not authorized for this resource.',
                    'required_roles': list(allowed_roles)
                }), 403

            return f(*args, **kwargs)

        return decorated

    return decorator
