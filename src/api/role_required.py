from functools import wraps
from flask import request, jsonify, current_app
import jwt
from sqlalchemy import select

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import RoleModel, UserModel, user_roles


def token_required(f):
    """Decorator kiá»ƒm tra JWT Token há»£p lá»‡"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Láº¥y token tá»« Authorization Header
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

            session = db_factory.get_database('POSTGREE').session
            user = session.query(UserModel).filter_by(id=request.user['user_id']).first()
            if user and user.status != 'active':
                return jsonify({'message': 'User account is locked or no longer exists.'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired! Please login again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """Decorator kiá»ƒm tra JWT Token vÃ  xÃ¡c thá»±c Vai trÃ² (Role) cá»§a ngÆ°á»i dÃ¹ng"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            user_role = request.user.get('role')
            if user_role == 'admin' and allowed_roles == ('admin',):
                session = db_factory.get_database('POSTGREE').session
                user_id = request.user.get('user_id')
                user = session.query(UserModel).filter_by(id=user_id).first()
                if user:
                    user_role = session.execute(
                        select(RoleModel.code)
                        .select_from(user_roles)
                        .join(RoleModel, user_roles.c.role_id == RoleModel.id)
                        .where(user_roles.c.user_id == user.id)
                    ).scalar() or 'participant'
                    request.user['role'] = user_role
            if allowed_roles and user_role not in allowed_roles:
                return jsonify({
                    'message': f'Access forbidden! Role "{user_role}" is not authorized for this resource.',
                    'required_roles': list(allowed_roles)
                }), 403

            return f(*args, **kwargs)

        return decorated

    return decorator
