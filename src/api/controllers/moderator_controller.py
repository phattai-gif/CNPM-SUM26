from flask import Blueprint, jsonify, request

from api.role_required import role_required
from services.moderator_dashboard_service import ModeratorDashboardService


moderator_bp = Blueprint('moderator', __name__, url_prefix='/moderator')
moderator_service = ModeratorDashboardService()


def _filters():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
    status = request.args.get('status')
    ai_risk = request.args.get('ai_risk')
    if status and status not in {'submitted', 'flagged'}:
        raise ValueError('status must be submitted or flagged')
    if ai_risk and ai_risk not in {'safe', 'medium', 'high'}:
        raise ValueError('ai_risk must be safe, medium, or high')
    return page, per_page, status, ai_risk


@moderator_bp.route('/dashboard', methods=['GET'])
@role_required('organizer', 'admin')
def dashboard():
    try:
        contest_id = request.args.get('contest_id', type=int)
        data = moderator_service.dashboard(request.user['user_id'], request.user['role'], contest_id)
        return jsonify({'message': 'Moderator dashboard data retrieved successfully', **data}), 200
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 404
    except PermissionError as exc:
        return jsonify({'message': str(exc)}), 403
    except Exception as exc:
        return jsonify({'message': 'Unable to load moderator dashboard', 'error': str(exc)}), 500


@moderator_bp.route('/submissions', methods=['GET'])
@role_required('organizer', 'admin')
def submissions():
    try:
        page, per_page, status, ai_risk = _filters()
        data = moderator_service.submissions(
            request.user['user_id'], request.user['role'], request.args.get('contest_id', type=int),
            page, per_page, status, ai_risk,
        )
        return jsonify(data), 200
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except PermissionError as exc:
        return jsonify({'message': str(exc)}), 403
    except Exception as exc:
        return jsonify({'message': 'Unable to load moderator submissions', 'error': str(exc)}), 500