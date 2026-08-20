import hashlib
import os
import uuid

from pathlib import Path
from typing import Any, Dict, Optional

try:
    from domain.services.istorage_service import (
        IStorageAdapter,
    )
except ImportError:
    from domain.services.istorage_service import (
        IStorageAdapter,
    )


class LocalStorageAdapter(IStorageAdapter):
    """
    Local storage adapter.

    Used for development and testing when
    STORAGE_PROVIDER=local.
    """

    def __init__(
        self,
        upload_folder: Optional[str] = None,
        base_url: str = "",
    ):
        if upload_folder is None:
            upload_folder = str(
                Path(__file__).resolve().parents[4]
                / "frontend"
                / "static"
                / "uploads"
            )
        self.upload_folder = os.path.abspath(
            upload_folder
        )

        if base_url:
            clean_base = base_url.rstrip("/")

            if clean_base.endswith(
                "/static/uploads"
            ):
                self.base_url = clean_base
            else:
                self.base_url = (
                    f"{clean_base}/static/uploads"
                )
        else:
            self.base_url = "/static/uploads"

        os.makedirs(
            self.upload_folder,
            exist_ok=True,
        )

    def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        thumbnail_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        if not file_bytes:
            raise ValueError(
                "File content is empty"
            )

        file_hash = hashlib.sha256(
            file_bytes
        ).hexdigest()[:12]

        unique_prefix = (
            f"{file_hash}_"
            f"{uuid.uuid4().hex[:8]}"
        )

        extension = (
            os.path.splitext(filename)[1].lower()
            if filename
            else ""
        )

        if not extension:
            if "jpeg" in content_type:
                extension = ".jpg"
            else:
                extension = ".png"

        # -----------------------------------------------------
        # HD image
        # -----------------------------------------------------

        hd_filename = (
            f"hd_{unique_prefix}{extension}"
        )

        hd_path = os.path.join(
            self.upload_folder,
            hd_filename,
        )

        with open(hd_path, "wb") as file:
            file.write(file_bytes)

        hd_url = (
            f"{self.base_url}/{hd_filename}"
        )

        # -----------------------------------------------------
        # Thumbnail
        # -----------------------------------------------------

        thumbnail_url = None

        if thumbnail_bytes:
            thumbnail_filename = (
                f"thumb_{unique_prefix}.jpg"
            )

            thumbnail_path = os.path.join(
                self.upload_folder,
                thumbnail_filename,
            )

            with open(
                thumbnail_path,
                "wb",
            ) as file:
                file.write(thumbnail_bytes)

            thumbnail_url = (
                f"{self.base_url}/"
                f"{thumbnail_filename}"
            )

        return {
            "hd_url": hd_url,
            "thumbnail_url": (
                thumbnail_url
                or hd_url
            ),
        }
