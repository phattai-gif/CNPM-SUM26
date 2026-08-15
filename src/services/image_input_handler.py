import os
import tempfile
from contextlib import contextmanager
from PIL import Image

class ImageInputHandler:
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}

    @classmethod
    @contextmanager
    def temp_image_context(cls, file_storage, max_size_mb=15):
        """
        Context manager to validate an uploaded file, save it to a cross-platform
        temp directory, yield the path, and automatically clean it up.
        
        Yields:
            str: Path to the temporary image file.
            
        Raises:
            ValueError: If validation fails (e.g. wrong format, empty file, size limit exceeded, or corrupted image).
        """
        if not file_storage:
            raise ValueError("No file provided")

        filename = file_storage.filename
        if not filename:
            raise ValueError("No selected file")

        # 1. Verify extension
        _, ext = os.path.splitext(filename.lower())
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension: '{ext}'. Allowed: {', '.join(sorted(cls.ALLOWED_EXTENSIONS))}"
            )

        # 2. Verify file size
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)  # Reset pointer to the beginning

        if file_size == 0:
            raise ValueError("Uploaded file is empty")

        max_bytes = max_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise ValueError(
                f"File size exceeds limit of {max_size_mb}MB (got {file_size / (1024 * 1024):.2f}MB)"
            )

        # 3. Create a unique, cross-platform temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        temp_path = temp_file.name
        temp_file.close()

        try:
            # Save the file to the temp path
            file_storage.save(temp_path)

            # 4. Verify image content is not corrupted using PIL
            try:
                with Image.open(temp_path) as img:
                    img.verify()
            except Exception as e:
                raise ValueError(f"Invalid or corrupted image file: {str(e)}")

            yield temp_path

        finally:
            # 5. Guaranteed cleanup of the temporary file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
