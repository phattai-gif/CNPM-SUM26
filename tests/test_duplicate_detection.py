import sys
import os

# Thêm đường dẫn src vào sys.path để import module service
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.duplicate_detection_service import DuplicateDetectionService


def test_duplicate_detection_service():
    image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tests/test_images'))
    if not os.path.isdir(image_dir):
        raise FileNotFoundError(f"Image folder not found: {image_dir}")

    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))]
    if len(image_files) < 2:
        raise ValueError(f"Need at least 2 image files in {image_dir}. Found: {image_files}")

    image_files.sort()
    new_image = os.path.join(image_dir, image_files[0])
    existing_image = os.path.join(image_dir, image_files[1])

    service = DuplicateDetectionService()
    result = service.check_duplicate(new_image, existing_image)

    print('new_image:', new_image)
    print('existing_image:', existing_image)
    print('result:', result)

    assert isinstance(result, dict)
    assert 'similarity_score' in result
    assert 'is_duplicate' in result


if __name__ == '__main__':
    test_duplicate_detection_service()
