import os
from flask import Blueprint, request
from api.controllers.response_utils import safe_jsonify

try:
    from services.ai_detection_service import AiDetectionService
    from services.image_input_handler import ImageInputHandler
except ImportError:
    from services.ai_detection_service import AiDetectionService
    from services.image_input_handler import ImageInputHandler

bp = Blueprint('ai_detection', __name__, url_prefix='/ai-detection')
service = AiDetectionService()


@bp.route('/check', methods=['POST'])
def check_ai_detection():
    """Check if an uploaded image is likely AI-generated."""
    if 'image' not in request.files:
        return jsonify({'error': 'Missing image file'}), 400

    file = request.files['image']
    try:
        with ImageInputHandler.temp_image_context(file) as temp_path:
            result = service.detect_ai(temp_path)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error during image analysis: {str(e)}"}), 500

    return safe_jsonify(result, status=200)


