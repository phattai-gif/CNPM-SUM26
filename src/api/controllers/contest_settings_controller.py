from flask import Blueprint, request, jsonify
from api.role_required import token_required, role_required
from services.contest_settings_service import ContestSettingsService
from infrastructure.repositories.contest_settings_repository import ContestSettingsRepository

contest_settings_bp = Blueprint('contest_settings', __name__, url_prefix='/contests')
contest_settings_service = ContestSettingsService(ContestSettingsRepository())


@contest_settings_bp.route('/<int:contest_id>/settings', methods=['GET'])
@token_required
def get_contest_settings(contest_id):
    """
    Get settings for a specific contest
    ---
    get:
      summary: Retrieve contest settings
      tags:
        - Contest Settings
      security:
        - Bearer: []
      parameters:
        - in: path
          name: contest_id
          schema:
            type: integer
          required: true
      responses:
        200:
          description: Contest settings
        404:
          description: Contest settings not found
    """
    settings = contest_settings_service.get_contest_settings(contest_id)
    if not settings:
        return jsonify({'message': 'Contest settings not found'}), 404
    
    return jsonify({
        'contest_id': settings.contest_id,
        'allow_ai_submission': settings.allow_ai_submission,
        'require_manual_review': settings.require_manual_review,
        'auto_calculate_scores': settings.auto_calculate_scores,
        'created_at': settings.created_at.isoformat() if settings.created_at else None,
        'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
    }), 200


@contest_settings_bp.route('/<int:contest_id>/settings', methods=['POST', 'PUT'])
@role_required('organizer')
def update_contest_settings(contest_id):
    """
    Create or update settings for a contest
    """
    data = request.get_json(silent=True) or {}
    
    # Extract allowed fields with strict type validation
    update_data = {}
    for key in ('allow_ai_submission', 'require_manual_review', 'auto_calculate_scores'):
        if key in data:
            val = data[key]
            if not isinstance(val, bool):
                return jsonify({'message': f'{key} must be a boolean'}), 400
            update_data[key] = val
    
    try:
        settings = contest_settings_service.create_or_update_settings(contest_id, **update_data)
        if not settings:
            return jsonify({'message': 'Contest not found or unable to update settings'}), 404

        return jsonify({
            'contest_id': settings.contest_id,
            'allow_ai_submission': settings.allow_ai_submission,
            'require_manual_review': settings.require_manual_review,
            'auto_calculate_scores': settings.auto_calculate_scores,
            'created_at': settings.created_at.isoformat() if settings.created_at else None,
            'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
            'message': 'Contest settings updated'
        }), 200
    except ValueError as exc:
        return jsonify({'message': str(exc)}), 400
    except Exception as exc:
        return jsonify({'message': 'Failed to update contest settings', 'error': str(exc)}), 500

