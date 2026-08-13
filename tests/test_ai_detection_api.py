import os
import sys
import io
import contextlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ['POSTGREE_DATABASE_URL'] = 'sqlite:///:memory:'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        app = create_app()
    client = app.test_client()

    image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_images'))
    if not os.path.isdir(image_dir):
        raise FileNotFoundError(f"Folder not found: {image_dir}")

    image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))]
    image_files.sort()

    for file_name in image_files:
        image_path = os.path.join(image_dir, file_name)
        with open(image_path, 'rb') as img_file:
            data = {
                'image': (io.BytesIO(img_file.read()), file_name)
            }
            resp = client.post(
                '/ai-detection/check',
                data=data,
                content_type='multipart/form-data'
            )
        print(f"file: {file_name}")
        print(f"status_code: {resp.status_code}")
        print(f"response: {resp.get_json()}\n")


if __name__ == '__main__':
    main()
