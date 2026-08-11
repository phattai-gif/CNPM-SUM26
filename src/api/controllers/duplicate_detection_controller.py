from flask import Blueprint, request, jsonify

try:
    from src.services.duplicate_detection_service import DuplicateDetectionService
except ImportError:
    from services.duplicate_detection_service import DuplicateDetectionService

bp = Blueprint('duplicate_detection', __name__, url_prefix='/duplicate-detection')
service = DuplicateDetectionService()


@bp.route('/check', methods=['POST'])
def check_duplicate():
    """Compare two uploaded image files and report whether they are duplicates."""
    if 'new_image' not in request.files or 'existing_image' not in request.files:
        return jsonify({'error': 'Both new_image and existing_image are required'}), 400

    new_file = request.files['new_image']
    existing_file = request.files['existing_image']

    if not new_file.filename or not existing_file.filename:
        return jsonify({'error': 'Both files must be selected'}), 400

    new_path = f"/tmp/{new_file.filename}"
    existing_path = f"/tmp/{existing_file.filename}"

    new_file.save(new_path)
    existing_file.save(existing_path)

    result = service.check_duplicate(new_path, existing_path)
    return jsonify(result), 200
