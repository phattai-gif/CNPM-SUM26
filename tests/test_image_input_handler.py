import os
import sys
import io
from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Insert src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from services.image_input_handler import ImageInputHandler

class MockFileStorage:
    def __init__(self, filename, stream):
        self.filename = filename
        self.stream = stream

    def seek(self, *args, **kwargs):
        return self.stream.seek(*args, **kwargs)

    def tell(self, *args, **kwargs):
        return self.stream.tell(*args, **kwargs)

    def save(self, dst_path):
        self.stream.seek(0)
        with open(dst_path, 'wb') as f:
            f.write(self.stream.read())


def test_image_input_handler():
    print("Running ImageInputHandler tests...")

    # Load a real image for validation testing
    image_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_images'))
    real_image_path = os.path.join(image_dir, 'anh_can_quet3.jpg')
    with open(real_image_path, 'rb') as f:
        real_image_data = f.read()

    # 1. Test valid image
    stream = io.BytesIO(real_image_data)
    mock_file = MockFileStorage('test.jpg', stream)
    with ImageInputHandler.temp_image_context(mock_file) as temp_path:
        assert os.path.exists(temp_path)
        assert temp_path.endswith('.jpg')
        print("OK - Valid image test passed. Temp path:", temp_path)
    # Check that it's deleted afterwards
    assert not os.path.exists(temp_path)
    print("OK - Valid image temp file cleanup test passed.")

    # 2. Test invalid extension
    stream = io.BytesIO(real_image_data)
    mock_file = MockFileStorage('test.txt', stream)
    try:
        with ImageInputHandler.temp_image_context(mock_file) as temp_path:
            raise AssertionError("Should have raised ValueError for invalid extension")
    except ValueError as e:
        assert "Unsupported file extension" in str(e)
        print("OK - Invalid extension test passed. Message:", str(e))

    # 3. Test empty file
    stream = io.BytesIO(b'')
    mock_file = MockFileStorage('test.png', stream)
    try:
        with ImageInputHandler.temp_image_context(mock_file) as temp_path:
            raise AssertionError("Should have raised ValueError for empty file")
    except ValueError as e:
        assert "Uploaded file is empty" in str(e)
        print("OK - Empty file test passed. Message:", str(e))

    # 4. Test oversized file (limit set to 1MB, file is ~93KB, let's limit it to 0.05MB = 50KB)
    stream = io.BytesIO(real_image_data)
    mock_file = MockFileStorage('test.png', stream)
    try:
        with ImageInputHandler.temp_image_context(mock_file, max_size_mb=0.05) as temp_path:
            raise AssertionError("Should have raised ValueError for oversized file")
    except ValueError as e:
        assert "File size exceeds limit" in str(e)
        print("OK - Oversized file test passed. Message:", str(e))

    # 5. Test corrupted image file
    stream = io.BytesIO(b'corrupted data content that is not an image')
    mock_file = MockFileStorage('corrupt.png', stream)
    try:
        with ImageInputHandler.temp_image_context(mock_file) as temp_path:
            raise AssertionError("Should have raised ValueError for corrupted image")
    except ValueError as e:
        assert "Invalid or corrupted image file" in str(e)
        print("OK - Corrupted file test passed. Message:", str(e))

    print("All ImageInputHandler tests completed successfully!")


if __name__ == '__main__':
    test_image_input_handler()
