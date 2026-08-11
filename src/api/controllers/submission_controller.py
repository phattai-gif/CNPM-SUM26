from datetime import datetime

from flask import Blueprint, jsonify, request

try:
    from src.api.role_required import token_required
    from src.infrastructure.repositories.submission_repository import SubmissionRepository
except ImportError:
    from api.role_required import token_required
    from infrastructure.repositories.submission_repository import SubmissionRepository

submission_bp = Blueprint('submission', __name__, url_prefix='/submissions')
submission_repo = SubmissionRepository()


@submission_bp.route('/health', methods=['GET'])
def submission_health():
    return jsonify({'message': 'Submission router is working!'}), 200


@submission_bp.route('', methods=['POST'])
@token_required
def create_submission():
    data = request.get_json(silent=True) or {}

    required_fields = ['round_id', 'title', 'image_hd_url']
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        return jsonify({
            'message': 'Missing required fields',
            'missing_fields': missing,
        }), 400

    user_id = request.user.get('user_id')
    if not user_id:
        return jsonify({'message': 'User information is missing in token'}), 401

    metadata = data.get('film_metadata') or {}
    submission = submission_repo.create_submission(
        round_id=data['round_id'],
        user_id=user_id,
        title=data['title'],
        story_description=data.get('story_description', ''),
        image_hd_url=data['image_hd_url'],
        thumbnail_url=data.get('thumbnail_url'),
        width_px=data.get('width_px'),
        height_px=data.get('height_px'),
        file_size_bytes=data.get('file_size_bytes'),
        file_hash=data.get('file_hash'),
        film_stock=metadata.get('film_stock'),
        film_iso=metadata.get('film_iso'),
        camera_body=metadata.get('camera_body'),
        lens=metadata.get('lens'),
        lab_name=metadata.get('lab_name'),
        scanner_info=metadata.get('scanner_info'),
        development_process=metadata.get('development_process', 'C-41'),
        taken_at_location=metadata.get('taken_at_location'),
        status=data.get('status', 'submitted'),
    )

    return jsonify({
        'message': 'Submission created successfully',
        'submission': {
            'id': submission.id,
            'round_id': submission.round_id,
            'user_id': submission.user_id,
            'title': submission.title,
            'story_description': submission.story_description,
            'status': submission.status,
            'submitted_at': submission.submitted_at,
        }
    }), 201


@submission_bp.route('/<int:submission_id>', methods=['GET'])
@token_required
def get_submission(submission_id):
    submission = submission_repo.get_by_id(submission_id)
    if not submission:
        return jsonify({'message': 'Submission not found'}), 404
    return jsonify({
        'id': submission.id,
        'round_id': submission.round_id,
        'user_id': submission.user_id,
        'title': submission.title,
        'story_description': submission.story_description,
        'status': submission.status,
        'submitted_at': submission.submitted_at,
        'created_at': submission.created_at,
        'updated_at': submission.updated_at,
    }), 200


@submission_bp.route('', methods=['GET'])
@token_required
def list_submissions():
    submissions = submission_repo.list()
    return jsonify([
        {
            'id': item.id,
            'round_id': item.round_id,
            'user_id': item.user_id,
            'title': item.title,
            'story_description': item.story_description,
            'status': item.status,
            'submitted_at': item.submitted_at,
        }
        for item in submissions
    ]), 200
