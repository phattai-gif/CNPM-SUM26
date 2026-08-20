import hashlib
import io
import os

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PIL import Image

try:
    from config import Config
    from domain.services.istorage_service import (
        IStorageAdapter,
    )
    from infrastructure.services.storage.local_storage_adapter import (
        LocalStorageAdapter,
    )
    from infrastructure.services.storage.cloudinary_storage_adapter import (
        CloudinaryStorageAdapter,
    )
except ImportError:
    from config import Config
    from domain.services.istorage_service import (
        IStorageAdapter,
    )
    from infrastructure.services.storage.local_storage_adapter import (
        LocalStorageAdapter,
    )
    from infrastructure.services.storage.cloudinary_storage_adapter import (
        CloudinaryStorageAdapter,
    )


ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
}

ALLOWED_MIMETYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "image/pjpeg",
    "image/x-png",
}


class StorageService:
    """
    Application-level storage service.

    Responsibilities:
    - Validate image
    - Check size
    - Check MIME type
    - Verify image integrity
    - Calculate SHA-256
    - Extract dimensions
    - Generate thumbnail
    - Delegate storage to adapter
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        adapter: Optional[IStorageAdapter] = None,
    ):
        if adapter is not None:
            self.adapter = adapter
            self.provider_name = "custom"
            return

        self.provider_name = (
            provider
            or getattr(
                Config,
                "STORAGE_PROVIDER",
                "local",
            )
        ).lower().strip()

        self.adapter = self._init_adapter(
            self.provider_name
        )

    def _init_adapter(
        self,
        provider_name: str,
    ) -> IStorageAdapter:

        upload_folder = getattr(
            Config,
            "UPLOAD_FOLDER",
            str(
                Path(__file__).resolve().parents[1]
                / "frontend"
                / "static"
                / "uploads"
            ),
        )

        base_url = getattr(
            Config,
            "BASE_URL",
            "http://localhost:9999",
        )

        if provider_name == "cloudinary":
            return CloudinaryStorageAdapter()

        return LocalStorageAdapter(
            upload_folder=upload_folder,
            base_url=base_url,
        )

    @staticmethod
    def validate_file(
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str] = None,
    ) -> None:

        if not file_bytes:
            raise ValueError(
                "File content is empty"
            )

        max_size = getattr(
            Config,
            "MAX_CONTENT_LENGTH",
            50 * 1024 * 1024,
        )

        if len(file_bytes) > max_size:
            max_size_mb = max_size // (
                1024 * 1024
            )

            raise ValueError(
                "File size exceeds maximum limit "
                f"of {max_size_mb}MB"
            )

        extension = (
            os.path.splitext(filename)[1].lower()
            if filename
            else ""
        )

        if (
            extension
            and extension not in ALLOWED_EXTENSIONS
        ):
            raise ValueError(
                f"Invalid file extension "
                f"'{extension}'. "
                "Allowed extensions: "
                f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        if content_type:
            cleaned_mime = (
                content_type
                .split(";")[0]
                .strip()
                .lower()
            )

            if (
                cleaned_mime
                not in ALLOWED_MIMETYPES
            ):
                raise ValueError(
                    f"Invalid file MIME type "
                    f"'{content_type}'. "
                    "Allowed image types only."
                )

    @staticmethod
    def _generate_thumbnail(
        image: Image.Image,
        max_thumb_size: Tuple[int, int],
    ) -> Optional[bytes]:

        try:
            thumbnail = image.copy()

            thumbnail.thumbnail(
                max_thumb_size
            )

            if thumbnail.mode not in (
                "RGB",
                "L",
            ):
                thumbnail = thumbnail.convert(
                    "RGB"
                )

            thumbnail_io = io.BytesIO()

            thumbnail.save(
                thumbnail_io,
                format="JPEG",
                quality=85,
                optimize=True,
            )

            return thumbnail_io.getvalue()

        except Exception as exc:
            print(
                "Warning: Failed to generate "
                f"thumbnail ({exc})"
            )
            return None

    def upload_image(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
        max_thumb_size: Tuple[int, int] = (
            300,
            300,
        ),
    ) -> Dict[str, Any]:

        self.validate_file(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

        sha256_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()

        file_size = len(file_bytes)

        # -----------------------------------------------------
        # Verify image
        # -----------------------------------------------------

        try:
            image = Image.open(
                io.BytesIO(file_bytes)
            )

            image.verify()

            image = Image.open(
                io.BytesIO(file_bytes)
            )

            width, height = image.size

        except Exception as exc:
            raise ValueError(
                "Invalid or corrupted image file"
            ) from exc

        # -----------------------------------------------------
        # Generate thumbnail
        # -----------------------------------------------------

        thumbnail_bytes = (
            self._generate_thumbnail(
                image=image,
                max_thumb_size=max_thumb_size,
            )
        )

        # -----------------------------------------------------
        # Store
        # -----------------------------------------------------

        storage_result = (
            self.adapter.save_file(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                thumbnail_bytes=thumbnail_bytes,
            )
        )

        hd_url = storage_result.get(
            "hd_url"
        )

        if not hd_url:
            raise ValueError(
                "Storage adapter did not return hd_url"
            )

        thumbnail_url = (
            storage_result.get(
                "thumbnail_url"
            )
            or hd_url
        )

        return {
            "hd_url": hd_url,
            "thumbnail_url": thumbnail_url,
            "file_size": file_size,
            "width": width,
            "height": height,
            "sha256": sha256_hash,
        }

