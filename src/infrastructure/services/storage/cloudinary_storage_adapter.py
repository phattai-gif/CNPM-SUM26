import io
import os

from typing import Any, Dict, Optional

try:
    from domain.services.istorage_service import (
        IStorageAdapter,
    )
except ImportError:
    from domain.services.istorage_service import (
        IStorageAdapter,
    )


class CloudinaryStorageAdapter(IStorageAdapter):
    """
    Cloudinary storage adapter.

    Used when STORAGE_PROVIDER=cloudinary.
    """

    def __init__(
        self,
        cloudinary_url: Optional[str] = None,
        cloud_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError as exc:
            raise ImportError(
                "cloudinary package is required. "
                "Install with: pip install cloudinary"
            ) from exc

        self.cloudinary = cloudinary
        self.cloudinary_uploader = cloudinary.uploader

        try:
            import cloudinary.utils

            self.cloudinary_utils = cloudinary.utils
        except ImportError:
            self.cloudinary_utils = None

        self.cloudinary_url = (
            cloudinary_url
            or os.environ.get("CLOUDINARY_URL")
        )

        self.cloud_name = (
            cloud_name
            or os.environ.get("CLOUDINARY_CLOUD_NAME")
        )

        self.api_key = (
            api_key
            or os.environ.get("CLOUDINARY_API_KEY")
        )

        self.api_secret = (
            api_secret
            or os.environ.get("CLOUDINARY_API_SECRET")
        )

        # -----------------------------------------------------
        # Configure Cloudinary
        # -----------------------------------------------------

        if self.cloudinary_url:
            self.cloudinary.config(
                cloudinary_url=self.cloudinary_url,
                secure=True,
            )

        elif (
            self.cloud_name
            and self.api_key
            and self.api_secret
        ):
            self.cloudinary.config(
                cloud_name=self.cloud_name,
                api_key=self.api_key,
                api_secret=self.api_secret,
                secure=True,
            )

        else:
            raise ValueError(
                "Cloudinary credentials must be configured using "
                "CLOUDINARY_URL or "
                "CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY and "
                "CLOUDINARY_API_SECRET."
            )

    def save_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        thumbnail_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Upload original image and thumbnail to Cloudinary.
        """

        if not file_bytes:
            raise ValueError(
                "File content is empty"
            )

        # -----------------------------------------------------
        # Upload original HD image
        # -----------------------------------------------------

        upload_result = self.cloudinary_uploader.upload(
            io.BytesIO(file_bytes),
            folder="submissions/hd",
            resource_type="image",
        )

        if not upload_result:
            raise ValueError(
                "Cloudinary upload returned an empty result"
            )

        hd_url = (
            upload_result.get("secure_url")
            or upload_result.get("url")
        )

        public_id = upload_result.get(
            "public_id"
        )

        if not hd_url:
            raise ValueError(
                "Cloudinary upload did not return an image URL"
            )

        # -----------------------------------------------------
        # Upload thumbnail
        # -----------------------------------------------------

        thumbnail_url = None
        thumbnail_public_id = None

        if thumbnail_bytes:
            thumbnail_result = (
                self.cloudinary_uploader.upload(
                    io.BytesIO(thumbnail_bytes),
                    folder="submissions/thumbnails",
                    resource_type="image",
                )
            )

            if thumbnail_result:
                thumbnail_url = (
                    thumbnail_result.get("secure_url")
                    or thumbnail_result.get("url")
                )

                thumbnail_public_id = (
                    thumbnail_result.get("public_id")
                )

        # -----------------------------------------------------
        # Fallback: Cloudinary transformation
        # -----------------------------------------------------

        if (
            not thumbnail_url
            and public_id
            and self.cloudinary_utils
        ):
            thumbnail_url, _ = (
                self.cloudinary_utils.cloudinary_url(
                    public_id,
                    width=300,
                    height=300,
                    crop="thumb",
                    secure=True,
                )
            )

        # -----------------------------------------------------
        # Final fallback
        # -----------------------------------------------------

        if not thumbnail_url:
            thumbnail_url = hd_url

        return {
            "hd_url": hd_url,
            "thumbnail_url": thumbnail_url,
            "public_id": public_id,
            "thumbnail_public_id": thumbnail_public_id,
        }
