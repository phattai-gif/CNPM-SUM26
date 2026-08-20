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

    if len(image_files) < 2:
        print("Need at least 2 images to check duplicate detection API")
        return

    # Check valid duplicate check
    new_image_name = image_files[0]
    existing_image_name = image_files[1]

    with open(os.path.join(image_dir, new_image_name), 'rb') as f1:
        data1 = f1.read()
    with open(os.path.join(image_dir, existing_image_name), 'rb') as f2:
        data2 = f2.read()

    data = {
        'new_image': (io.BytesIO(data1), new_image_name),
        'existing_image': (io.BytesIO(data2), existing_image_name)
    }

    resp = client.post(
        '/duplicate-detection/check',
        data=data,
        content_type='multipart/form-data'
    )
    print("duplicate detection API response status_code:", resp.status_code)
    print("response body:", resp.get_json())
    assert resp.status_code == 200


if __name__ == '__main__':
    main()
