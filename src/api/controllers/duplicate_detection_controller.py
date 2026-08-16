import os
from flask import Blueprint, request, jsonify

try:
    from services.duplicate_detection_service import DuplicateDetectionService
    from services.image_input_handler import ImageInputHandler
except ImportError:
    from services.duplicate_detection_service import DuplicateDetectionService
    from services.image_input_handler import ImageInputHandler

bp = Blueprint('duplicate_detection', __name__, url_prefix='/duplicate-detection')
service = DuplicateDetectionService()


@bp.route('/check', methods=['POST'])
def check_duplicate():
    if 'new_image' not in request.files or 'existing_image' not in request.files:
        return jsonify({'error': 'Both new_image and existing_image are required'}), 400

    new_file = request.files['new_image']
    existing_file = request.files['existing_image']

    try:
        with ImageInputHandler.temp_image_context(new_file) as new_path:
            with ImageInputHandler.temp_image_context(existing_file) as existing_path:
                result = service.check_duplicate(new_path, existing_path)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error during duplicate check: {str(e)}"}), 500

    return jsonify(result), 200


