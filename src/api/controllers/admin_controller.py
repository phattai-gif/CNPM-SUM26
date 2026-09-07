from flask import Blueprint, request
from api.controllers.response_utils import safe_jsonify

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
        return safe_jsonify({
            'users': users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
            },
        }, status=200)
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'message': 'Unable to list users', 'error': str(exc)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@role_required('admin')
def get_user(user_id):
    user = admin_user_service.get_user(user_id)
    if not user:
        return safe_jsonify({'message': 'User not found'}, status=404)
    return safe_jsonify({'user': user}, status=200)


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
        return safe_jsonify({'message': 'User role updated successfully', 'user': user}, status=200)
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
        return safe_jsonify({'message': 'User status updated successfully', 'user': user}, status=200)
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'message': 'Unable to update user status', 'error': str(exc)}), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@role_required('admin')
def delete_user(user_id):
    try:
        success = admin_user_service.delete_user(
            request.user['user_id'], user_id
        )
        if not success:
            return jsonify({'message': 'User not found'}), 404
        return safe_jsonify({'message': 'User deleted successfully', 'user_id': user_id}, status=200)
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'message': 'Unable to delete user', 'error': str(exc)}), 500


@admin_bp.route('/dashboard/metrics', methods=['GET'])
@role_required('admin')
def get_admin_metrics():
    try:
        from sqlalchemy import func
        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import (
            UserModel, RoleModel, user_roles,
            ContestModel, SubmissionModel, AIFlagModel
        )
        session = db_factory.get_database('POSTGREE').session

        # 1. Total users & Locked users
        total_users = session.query(func.count(UserModel.id)).scalar() or 0
        locked_users = session.query(func.count(UserModel.id)).filter(UserModel.status == 'locked').scalar() or 0

        # 2. Roles breakdown
        role_rows = (
            session.query(RoleModel.code, func.count(user_roles.c.user_id))
            .join(user_roles, RoleModel.id == user_roles.c.role_id)
            .group_by(RoleModel.code)
            .all()
        )
        roles = {code: count for code, count in role_rows}
        admins_count = roles.get('admin', 0)
        organizers_count = roles.get('organizer', 0)
        judges_count = roles.get('judge', 0)
        participants_count = roles.get('participant', 0)

        # 3. Contests stats
        total_contests = session.query(func.count(ContestModel.id)).scalar() or 0
        pending_contests = session.query(func.count(ContestModel.id)).filter(
            ContestModel.status.in_(['draft', 'pending', 'under_review', 'created'])
        ).scalar() or 0

        # 4. Submissions & AI Flags stats
        total_submissions = session.query(func.count(SubmissionModel.id)).scalar() or 0
        ai_flagged_count = session.query(func.count(AIFlagModel.id)).filter(
            AIFlagModel.status.in_(['flagged', 'pending', 'open'])
        ).scalar() or 0
        if ai_flagged_count == 0:
            ai_flagged_count = session.query(func.count(SubmissionModel.id)).filter(
                SubmissionModel.status == 'flagged'
            ).scalar() or 0

        # Helper to safely format datetime / string timestamps
        def _to_iso(dt):
            if not dt:
                return None
            if isinstance(dt, str):
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)

        # 5. Recent system activities feed
        activities = []
        recent_users = session.query(UserModel).order_by(UserModel.created_at.desc()).limit(5).all()
        for u in recent_users:
            activities.append({
                'id': f'user-{u.id}',
                'type': 'user',
                'title': f'Người dùng mới đăng ký: {u.full_name or u.username} (@{u.username})',
                'timestamp': _to_iso(u.created_at),
                'badge': 'TÀI KHOẢN'
            })

        recent_contests = session.query(ContestModel).order_by(ContestModel.created_at.desc()).limit(5).all()
        for c in recent_contests:
            activities.append({
                'id': f'contest-{c.id}',
                'type': 'contest',
                'title': f'Cuộc thi mới được tạo: #{c.id} - {c.title}',
                'timestamp': _to_iso(c.created_at),
                'badge': 'CUỘC THI'
            })

        recent_subs = session.query(SubmissionModel).order_by(SubmissionModel.created_at.desc()).limit(5).all()
        for s in recent_subs:
            activities.append({
                'id': f'sub-{s.id}',
                'type': 'submission',
                'title': f'Bài dự thi mới được nộp: #{s.id} - {s.title or "Untitled"}',
                'timestamp': _to_iso(s.created_at),
                'badge': 'BÀI THI'
            })

        activities.sort(key=lambda x: str(x['timestamp'] or ''), reverse=True)
        recent_activities = activities[:8]

        return jsonify({
            'metrics': {
                'total_users': total_users,
                'locked_users': locked_users,
                'admins_count': admins_count,
                'organizers_count': organizers_count,
                'judges_count': judges_count,
                'participants_count': participants_count,
                'total_contests': total_contests,
                'pending_contests': pending_contests,
                'total_submissions': total_submissions,
                'ai_flagged_submissions': ai_flagged_count,
            },
            'recent_activities': recent_activities
        }), 200
    except Exception as exc:
        return jsonify({'message': 'Unable to fetch metrics', 'error': str(exc)}), 500


@admin_bp.route('/dashboard', methods=['GET'])
def admin_dashboard():
    """Render dedicated Admin Dashboard HTML page."""
    from flask import render_template
    return render_template('admin_dashboard.html')