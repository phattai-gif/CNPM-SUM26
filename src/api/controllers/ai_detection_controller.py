import os
import tempfile
from flask import Blueprint, request, jsonify

try:
    from src.services.ai_detection_service import AiDetectionService
except ImportError:
    from services.ai_detection_service import AiDetectionService

bp = Blueprint('ai_detection', __name__, url_prefix='/ai-detection')
service = AiDetectionService()


@bp.route('/check', methods=['POST'])
def check_ai_detection():
    """Check if an uploaded image is likely AI-generated."""
    if 'image' not in request.files:
        return jsonify({'error': 'Missing image file'}), 400

    file = request.files['image']
    if not file.filename:
        return jsonify({'error': 'No selected file'}), 400

    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    file.save(temp_path)

    try:
        result = service.detect_ai(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify(result), 200

