import os
from flask import Blueprint, request
from api.controllers.response_utils import safe_jsonify

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
    if 'new_image' not in request.files:
        return jsonify({'error': 'new_image is required'}), 400

    new_file = request.files['new_image']
    existing_file = request.files.get('existing_image')

    try:
        if existing_file:
            with ImageInputHandler.temp_image_context(new_file) as new_path:
                with ImageInputHandler.temp_image_context(existing_file) as existing_path:
                    result = service.check_duplicate(new_path, existing_path)
        else:
            new_image_bytes = new_file.read()
            new_file.seek(0)
            result = service.check_duplicate_against_database(new_image_bytes)
    except ValueError as e:
        return safe_jsonify({'error': str(e)}, status=400)
    except Exception as e:
        return safe_jsonify({'error': f"Internal error during duplicate check: {str(e)}"}, status=500)

    return safe_jsonify(result, status=200)


