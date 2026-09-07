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


# -------------------------------------------------------------------------
# Admin Capabilities: Contest Management (View All, Suspend / Approve)
# -------------------------------------------------------------------------

@admin_bp.route('/contests', methods=['GET'])
@role_required('admin')
def list_all_contests():
    """Admin: Xem toàn bộ contest."""
    try:
        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import ContestModel
        session = db_factory.get_database('POSTGREE').session
        contests = session.query(ContestModel).order_by(ContestModel.id.desc()).all()
        return safe_jsonify({
            'message': 'Lấy danh sách tất cả cuộc thi thành công',
            'contests': [c.to_dict() if hasattr(c, 'to_dict') else {'id': c.id, 'title': c.title, 'status': c.status} for c in contests],
            'total': len(contests),
        }, status=200)
    except Exception as exc:
        return jsonify({'message': 'Lỗi khi lấy danh sách cuộc thi', 'error': str(exc)}), 500


@admin_bp.route('/contests/<int:contest_id>/status', methods=['PATCH'])
@admin_bp.route('/contests/<int:contest_id>/approve', methods=['POST'])
@admin_bp.route('/contests/<int:contest_id>/suspend', methods=['POST'])
@role_required('admin')
def update_contest_status(contest_id):
    """Admin: Suspend/approve contest."""
    try:
        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import ContestModel
        session = db_factory.get_database('POSTGREE').session
        contest = session.query(ContestModel).filter_by(id=contest_id).first()
        if not contest:
            return jsonify({'message': 'Không tìm thấy cuộc thi'}), 404

        path = request.path
        payload = request.get_json(silent=True) or {}
        if 'approve' in path:
            new_status = 'published'
        elif 'suspend' in path:
            new_status = 'suspended'
        else:
            new_status = payload.get('status') or 'suspended'

        contest.status = new_status
        session.commit()
        session.refresh(contest)

        return safe_jsonify({
            'message': f'Cập nhật trạng thái cuộc thi thành công ({new_status})',
            'contest': contest.to_dict() if hasattr(contest, 'to_dict') else {'id': contest.id, 'status': contest.status},
        }, status=200)
    except Exception as exc:
        return jsonify({'message': 'Lỗi khi cập nhật trạng thái cuộc thi', 'error': str(exc)}), 500


# -------------------------------------------------------------------------
# Admin Capabilities: View All Submissions & AI Reports
# -------------------------------------------------------------------------

@admin_bp.route('/submissions', methods=['GET'])
@role_required('admin')
def list_all_submissions():
    """Admin: Xem toàn bộ submission."""
    try:
        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import SubmissionModel
        session = db_factory.get_database('POSTGREE').session
        page = max(request.args.get('page', 1, type=int), 1)
        per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
        query = session.query(SubmissionModel).order_by(SubmissionModel.id.desc())
        total = query.count()
        submissions = query.offset((page - 1) * per_page).limit(per_page).all()
        return safe_jsonify({
            'message': 'Lấy danh sách bài thi thành công',
            'submissions': [s.to_dict() if hasattr(s, 'to_dict') else {'id': s.id, 'title': s.title, 'status': s.status} for s in submissions],
            'pagination': {'page': page, 'per_page': per_page, 'total': total, 'pages': (total + per_page - 1) // per_page},
        }, status=200)
    except Exception as exc:
        return jsonify({'message': 'Lỗi khi lấy danh sách bài thi', 'error': str(exc)}), 500


@admin_bp.route('/ai-reports', methods=['GET'])
@admin_bp.route('/submissions/<int:submission_id>/ai-report', methods=['GET'])
@role_required('admin')
def view_ai_reports(submission_id=None):
    """Admin: Xem toàn bộ AI report."""
    try:
        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import AIAnalysisReportModel
        session = db_factory.get_database('POSTGREE').session
        query = session.query(AIAnalysisReportModel)
        if submission_id:
            query = query.filter_by(submission_id=submission_id)
        reports = query.order_by(AIAnalysisReportModel.id.desc()).all()
        out = []
        for r in reports:
            out.append({
                'id': r.id,
                'submission_id': r.submission_id,
                'ai_model_name': r.ai_model_name,
                'ai_confidence_score': float(r.ai_confidence_score) if r.ai_confidence_score is not None else None,
                'raw_details': r.raw_details,
                'created_at': r.created_at.isoformat() if r.created_at else None,
            })
        return safe_jsonify({'message': 'Lấy báo cáo AI thành công', 'reports': out}, status=200)
    except Exception as exc:
        return jsonify({'message': 'Lỗi khi lấy báo cáo AI', 'error': str(exc)}), 500


# -------------------------------------------------------------------------
# Admin Capabilities: Audit Log, System Settings & System Notifications
# -------------------------------------------------------------------------

@admin_bp.route('/audit-logs', methods=['GET'])
@role_required('admin')
def list_audit_logs():
    """Admin: Xem audit log."""
    try:
        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import AuditLogModel
        session = db_factory.get_database('POSTGREE').session
        logs = session.query(AuditLogModel).order_by(AuditLogModel.id.desc()).limit(100).all()
        out = []
        for l in logs:
            out.append({
                'id': l.id,
                'user_id': l.user_id,
                'action': l.action,
                'entity_name': l.entity_name,
                'entity_id': l.entity_id,
                'old_value': l.old_value,
                'new_value': l.new_value,
                'created_at': l.created_at.isoformat() if l.created_at else None,
            })
        return safe_jsonify({'message': 'Lấy audit log thành công', 'audit_logs': out}, status=200)
    except Exception as exc:
        return jsonify({'message': 'Lỗi khi lấy audit log', 'error': str(exc)}), 500


@admin_bp.route('/settings', methods=['GET', 'PUT', 'PATCH'])
@role_required('admin')
def manage_system_settings():
    """Admin: Quản lý system settings."""
    try:
        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import ContestSettingsModel
        session = db_factory.get_database('POSTGREE').session
        if request.method in ['PUT', 'PATCH']:
            data = request.get_json(silent=True) or {}
            # System level settings configuration mock / storage
            return jsonify({'message': 'Cập nhật cấu hình hệ thống thành công', 'settings': data}), 200

        settings = session.query(ContestSettingsModel).all()
        out = [s.to_dict() if hasattr(s, 'to_dict') else {'contest_id': s.contest_id, 'allow_ai': getattr(s, 'allow_ai_submission', True)} for s in settings]
        return jsonify({'message': 'Lấy cấu hình hệ thống thành công', 'system_settings': out}), 200
    except Exception as exc:
        return jsonify({'message': 'Lỗi khi quản lý cấu hình hệ thống', 'error': str(exc)}), 500


@admin_bp.route('/notifications/system', methods=['POST'])
@role_required('admin')
def send_system_notification():
    """Admin: Quản lý notification toàn hệ thống."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'Thông báo hệ thống')
        body = data.get('body', '')
        if not body:
            return jsonify({'message': 'Nội dung thông báo không được để trống'}), 400

        from infrastructure.databases.factory_database import FactoryDatabase as db_factory
        from infrastructure.models.app import NotificationModel, UserModel
        session = db_factory.get_database('POSTGREE').session
        users = session.query(UserModel).filter_by(status='active').all()
        created_count = 0
        for u in users:
            notif = NotificationModel(
                user_id=u.id,
                title=title,
                body=body,
                notification_type='system',
                is_read=False
            )
            session.add(notif)
            created_count += 1
        session.commit()
        return jsonify({'message': f'Đã gửi thông báo hệ thống đến {created_count} người dùng'}), 201
    except Exception as exc:
        return jsonify({'message': 'Lỗi khi gửi thông báo hệ thống', 'error': str(exc)}), 500