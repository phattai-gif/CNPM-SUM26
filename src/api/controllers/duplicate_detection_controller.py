import os
import tempfile
from flask import Blueprint, request, jsonify

try:
    from src.services.duplicate_detection_service import DuplicateDetectionService
except ImportError:
    from services.duplicate_detection_service import DuplicateDetectionService

bp = Blueprint('duplicate_detection', __name__, url_prefix='/duplicate-detection')
service = DuplicateDetectionService()


@bp.route('/check', methods=['POST'])
def check_duplicate():
    if 'new_image' not in request.files or 'existing_image' not in request.files:
        return jsonify({'error': 'Both new_image and existing_image are required'}), 400

    new_file = request.files['new_image']
    existing_file = request.files['existing_image']

    if not new_file.filename or not existing_file.filename:
        return jsonify({'error': 'Both files must be selected'}), 400

    temp_dir = tempfile.gettempdir()
    new_path = os.path.join(temp_dir, new_file.filename)
    existing_path = os.path.join(temp_dir, existing_file.filename)

    new_file.save(new_path)
    existing_file.save(existing_path)

    try:
        result = service.check_duplicate(new_path, existing_path)
    finally:
        if os.path.exists(new_path):
            os.remove(new_path)
        if os.path.exists(existing_path):
            os.remove(existing_path)

    return jsonify(result), 200

