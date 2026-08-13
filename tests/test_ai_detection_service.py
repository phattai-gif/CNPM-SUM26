import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from services.ai_detection_service import AiDetectionService


def main():
    image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_images'))
    if not os.path.isdir(image_dir):
        raise FileNotFoundError(f"Folder not found: {image_dir}")

    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))]
    image_files.sort()

    service = AiDetectionService()

    for file_name in image_files:
        image_path = os.path.join(image_dir, file_name)
        result = service.detect_ai(image_path)
        print(f"file: {file_name}")
        print(f"result: {result}\n")


if __name__ == '__main__':
    main()
