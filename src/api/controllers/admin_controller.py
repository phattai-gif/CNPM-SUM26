from flask import Blueprint, jsonify, request

from api.role_required import role_required
from api.schemas.admin_user import AdminRoleUpdateSchema, AdminStatusUpdateSchema
from services.admin_user_service import AdminUserService


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
admin_user_service = AdminUserService()
role_schema = AdminRoleUpdateSchema()
status_schema = AdminStatusUpdateSchema()


@admin_bp.route('/users', methods=['GET'])
@role_required('admin')
def list_users():
    try:
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        users, total = admin_user_service.list_users(
            page=page,
            per_page=per_page,
            search=request.args.get('search'),
            role=request.args.get('role'),
            status=request.args.get('status'),
        )
        return jsonify({
            'users': users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
            },
        }), 200
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'message': 'Unable to list users', 'error': str(exc)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@role_required('admin')
def get_user(user_id):
    user = admin_user_service.get_user(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    return jsonify({'user': user}), 200


@admin_bp.route('/users/<int:user_id>/role', methods=['PATCH'])
@role_required('admin')
def change_role(user_id):
    errors = role_schema.validate(request.get_json(silent=True) or {})
    if errors:
        return jsonify({'message': 'Validation error', 'errors': errors}), 400
    try:
        user = admin_user_service.change_role(
            request.user['user_id'], user_id, request.get_json()['role']
        )
        if not user:
            return jsonify({'message': 'User not found'}), 404
        return jsonify({'message': 'User role updated successfully', 'user': user}), 200
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'message': 'Unable to update user role', 'error': str(exc)}), 500


@admin_bp.route('/users/<int:user_id>/status', methods=['PATCH'])
@role_required('admin')
def change_status(user_id):
    errors = status_schema.validate(request.get_json(silent=True) or {})
    if errors:
        return jsonify({'message': 'Validation error', 'errors': errors}), 400
    try:
        user = admin_user_service.change_status(
            request.user['user_id'], user_id, request.get_json()['status']
        )
        if not user:
            return jsonify({'message': 'User not found'}), 404
        return jsonify({'message': 'User status updated successfully', 'user': user}), 200
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'message': 'Unable to update user status', 'error': str(exc)}), 500