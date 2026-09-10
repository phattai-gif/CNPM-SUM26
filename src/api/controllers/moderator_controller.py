from flask import Blueprint, request
from api.controllers.response_utils import safe_jsonify

from api.role_required import role_required
from services.moderator_dashboard_service import ModeratorDashboardService
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.repositories.moderator_dashboard_repository import ModeratorDashboardRepository


moderator_bp = Blueprint('moderator', __name__, url_prefix='/moderator')
moderator_service = ModeratorDashboardService()


@moderator_bp.before_request
def _sync_moderator_repository_session():
    repository = getattr(moderator_service, 'repository', None)
    if isinstance(repository, ModeratorDashboardRepository):
        repository.session = db_factory.get_database('POSTGREE').session


def _request_user():
    user = getattr(request, 'user', None)
    return user if isinstance(user, dict) else {}


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
        user = _request_user()
        contest_id = request.args.get('contest_id', type=int)
        data = moderator_service.dashboard(user.get('user_id'), user.get('role'), contest_id)
        # Merge into a response dict safely
        resp = {'message': 'Moderator dashboard data retrieved successfully'}
        if isinstance(data, dict):
            resp.update(data)
        else:
            resp['data'] = data
        return safe_jsonify(resp, status=200)
    except ValueError as exc:
        return safe_jsonify({'message': str(exc)}, status=404)
    except PermissionError as exc:
        return safe_jsonify({'message': str(exc)}, status=403)
    except Exception as exc:
        return safe_jsonify({'message': 'Unable to load moderator dashboard', 'error': str(exc)}, status=500)


@moderator_bp.route('/submissions', methods=['GET'])
@role_required('organizer', 'admin')
def submissions():
    try:
        user = _request_user()
        page, per_page, status, ai_risk = _filters()
        data = moderator_service.submissions(
            user.get('user_id'), user.get('role'), request.args.get('contest_id', type=int),
            page, per_page, status, ai_risk,
        )
        return safe_jsonify(data, status=200)
    except ValueError as exc:
        return safe_jsonify({'message': str(exc)}, status=400)
    except PermissionError as exc:
        return safe_jsonify({'message': str(exc)}, status=403)
    except Exception as exc:
        return safe_jsonify({'message': 'Unable to load moderator submissions', 'error': str(exc)}, status=500)


@moderator_bp.route('/submissions/<int:submission_id>/ai-report', methods=['GET'])
@role_required('organizer', 'admin')
def submission_ai_report(submission_id):
    try:
        user = _request_user()
        contest_id = request.args.get('contest_id', type=int)
        data = moderator_service.ai_report(
            user.get('user_id'),
            user.get('role'),
            submission_id,
            contest_id,
        )
        return safe_jsonify(data, status=200)
    except ValueError as exc:
        return safe_jsonify({'message': str(exc)}, status=404)
    except PermissionError as exc:
        return safe_jsonify({'message': str(exc)}, status=403)
    except Exception as exc:
        return safe_jsonify({'message': 'Unable to load AI report', 'error': str(exc)}, status=500)


@moderator_bp.route('/submissions/<int:submission_id>/approve', methods=['POST'])
@role_required('organizer', 'admin')
def approve_submission(submission_id):
    return _moderate(submission_id, 'approve')


@moderator_bp.route('/submissions/<int:submission_id>/reject', methods=['POST'])
@role_required('organizer', 'admin')
def reject_submission(submission_id):
    return _moderate(submission_id, 'reject')


@moderator_bp.route('/submissions/<int:submission_id>/dismiss-flag', methods=['POST'])
@role_required('organizer', 'admin')
def dismiss_flag(submission_id):
    return _moderate(submission_id, 'dismiss-flag')


def _moderate(submission_id, action):
    try:
        user = _request_user()
        payload = request.get_json(silent=True) or {}
        review_notes = payload.get('review_notes')
        contest_id = payload.get('contest_id') or request.args.get('contest_id', type=int)
        if contest_id is not None:
            contest_id = int(contest_id)

        data = moderator_service.moderate(
            user.get('user_id'),
            user.get('role'),
            submission_id,
            action,
            contest_id=contest_id,
            review_notes=review_notes,
        )
        return safe_jsonify({'message': 'Moderation action completed', 'result': data}, status=200)
    except ValueError as exc:
        return safe_jsonify({'message': str(exc)}, status=404)
    except PermissionError as exc:
        return safe_jsonify({'message': str(exc)}, status=403)
    except Exception as exc:
        return safe_jsonify({'message': 'Unable to moderate submission', 'error': str(exc)}, status=500)