from functools import wraps
from flask import request, jsonify, current_app, redirect, flash
import jwt
from sqlalchemy import select

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import RoleModel, UserModel, user_roles


def _prefers_html_response():
    best = request.accept_mimetypes.best_match(['text/html', 'application/json'])
    return (
        request.method == 'GET'
        and best == 'text/html'
        and request.accept_mimetypes[best] > request.accept_mimetypes['application/json']
    )


def _unauthorized_response(message, redirect_path='/auth/login'):
    if _prefers_html_response():
        flash(message, 'warning')
        return redirect(redirect_path)
    return jsonify({'message': message}), 401


def _forbidden_response(message, allowed_roles):
    if _prefers_html_response():
        flash(message, 'warning')
        return redirect('/contests')
    return jsonify({
        'message': message,
        'required_roles': list(allowed_roles)
    }), 403


def _extract_bearer_token():
    auth_header = request.headers.get('Authorization', '').strip()
    if auth_header:
        if auth_header.lower().startswith('bearer '):
            parts = auth_header.split(' ', 1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()
        # Backward-compatible fallback when token is sent without Bearer prefix.
        return auth_header

    alt_header = request.headers.get('X-Access-Token', '').strip()
    if alt_header:
        return alt_header

    cookie_token = request.cookies.get('access_token') or request.cookies.get('authToken')
    if cookie_token:
        return cookie_token

    return None


def token_required(f):
    """Decorator kiá»ƒm tra JWT Token há»£p lá»‡"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_bearer_token()

        if not token:
            return _unauthorized_response('Bạn cần đăng nhập để truy cập trang này.')

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
                return _unauthorized_response('Tài khoản đã bị khóa hoặc không còn tồn tại.')
        except jwt.ExpiredSignatureError:
            return _unauthorized_response('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')
        except jwt.InvalidTokenError:
            return _unauthorized_response('Token xác thực không hợp lệ. Vui lòng đăng nhập lại.')

        return f(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    """Decorator kiá»ƒm tra JWT Token vÃ  xÃ¡c thá»±c Vai trÃ² (Role) cá»§a ngÆ°á»i dÃ¹ng"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            # normalize allowed_roles: permit passing lists/tuples or multiple args
            normalized = set()
            for r in allowed_roles:
                if isinstance(r, (list, tuple, set)):
                    for v in r:
                        if v:
                            normalized.add(str(v).lower())
                elif r:
                    normalized.add(str(r).lower())

            user_role = (request.user.get('role') or 'participant')
            user_role = str(user_role).lower()

            # If no allowed roles specified, allow any authenticated user
            if normalized and user_role not in normalized:
                return _forbidden_response(
                    'Bạn không có quyền truy cập khu vực quản lý này.',
                    normalized,
                )

            return f(*args, **kwargs)

        return decorated

    return decorator
