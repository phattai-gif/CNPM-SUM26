from flask import Blueprint, request, jsonify
from api.role_required import token_required, role_required
from services.contest_settings_service import ContestSettingsService
from infrastructure.repositories.contest_settings_repository import ContestSettingsRepository

contest_settings_bp = Blueprint('contest_settings', __name__, url_prefix='/contests')
contest_settings_service = ContestSettingsService(ContestSettingsRepository())


@contest_settings_bp.route('/<int:contest_id>/settings', methods=['GET'])
@token_required
def get_contest_settings(current_user, contest_id):
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
@token_required
@role_required(['organizer', 'admin'])
def update_contest_settings(current_user, contest_id):
    """
    Create or update settings for a contest
    ---
    post:
      summary: Create or update contest settings
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
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                allow_ai_submission:
                  type: boolean
                  example: true
                require_manual_review:
                  type: boolean
                  example: true
                auto_calculate_scores:
                  type: boolean
                  example: false
      responses:
        200:
          description: Settings updated/created successfully
        400:
          description: Invalid input
    """
    data = request.get_json() or {}
    
    # Extract allowed fields
    update_data = {}
    if 'allow_ai_submission' in data:
        update_data['allow_ai_submission'] = data['allow_ai_submission']
    if 'require_manual_review' in data:
        update_data['require_manual_review'] = data['require_manual_review']
    if 'auto_calculate_scores' in data:
        update_data['auto_calculate_scores'] = data['auto_calculate_scores']
    
    settings = contest_settings_service.create_or_update_settings(contest_id, **update_data)
    
    return jsonify({
        'contest_id': settings.contest_id,
        'allow_ai_submission': settings.allow_ai_submission,
        'require_manual_review': settings.require_manual_review,
        'auto_calculate_scores': settings.auto_calculate_scores,
        'created_at': settings.created_at.isoformat() if settings.created_at else None,
        'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
        'message': 'Contest settings updated'
    }), 200
