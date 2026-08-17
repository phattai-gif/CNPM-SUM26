from typing import Any, Dict, Optional, Tuple

from infrastructure.repositories.submission_repository import (
    SubmissionRepository,
)
from services.storage_service import StorageService
from infrastructure.models.app import (
    SubmissionModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
)


class SubmissionService:
    """
    Application Service for Submission workflows.

    Handles:
    - Image upload
    - Storage processing
    - Submission creation
    - Submission detail retrieval
    """

    def __init__(
        self,
        submission_repo: Optional[
            SubmissionRepository
        ] = None,
        storage_service: Optional[
            StorageService
        ] = None,
    ):
        self.submission_repo = (
            submission_repo
            or SubmissionRepository()
        )

        self.storage_service = (
            storage_service
            or StorageService()
        )

    def upload_submission_image(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
    ) -> Dict[str, Any]:

        return self.storage_service.upload_image(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

    def create_submission(
        self,
        round_id: int,
        user_id: int,
        title: str,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = "image/jpeg",
        image_hd_url: Optional[str] = None,
        file_hash: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        width_px: Optional[int] = None,
        height_px: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        film_metadata: Optional[
            Dict[str, Any]
        ] = None,
        story_description: str = "",
        status: str = "submitted",
    ) -> SubmissionModel:

        film_metadata = (
            film_metadata or {}
        )

        # -----------------------------------------------------
        # Upload image when raw file is provided
        # -----------------------------------------------------

        if (
            file_bytes
            and len(file_bytes) > 0
            and filename
        ):
            storage_info = (
                self.storage_service.upload_image(
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=(
                        content_type
                        or "image/jpeg"
                    ),
                )
            )

            image_hd_url = storage_info[
                "hd_url"
            ]

            thumbnail_url = storage_info[
                "thumbnail_url"
            ]

            file_hash = storage_info[
                "sha256"
            ]

            width_px = storage_info[
                "width"
            ]

            height_px = storage_info[
                "height"
            ]

            file_size_bytes = storage_info[
                "file_size"
            ]

        if not image_hd_url:
            raise ValueError(
                "image_hd_url is required"
            )

        if not file_hash:
            raise ValueError(
                "file_hash is required"
            )

        if not film_metadata.get(
            "film_stock"
        ):
            raise ValueError(
                "film_metadata.film_stock is required"
            )

        submission = self.submission_repo.create_submission(
            round_id=round_id,
            user_id=user_id,
            title=title,
            image_hd_url=image_hd_url,
            file_hash=file_hash,
            story_description=story_description,
            thumbnail_url=thumbnail_url,
            width_px=width_px,
            height_px=height_px,
            file_size_bytes=file_size_bytes,
            film_stock=film_metadata.get("film_stock"),
            film_iso=film_metadata.get("film_iso"),
            camera_body=film_metadata.get("camera_body"),
            lens=film_metadata.get("lens"),
            lab_name=film_metadata.get("lab_name"),
            scanner_info=film_metadata.get("scanner_info"),
            development_process=film_metadata.get("development_process", "C-41"),
            taken_at_location=film_metadata.get("taken_at_location"),
            status=status,
        )

        try:
            from services.ai_detection_service import AiDetectionService
            ai_service = AiDetectionService()
            ai_result = ai_service.detect_ai(image_hd_url)

            ai_score = ai_result.get("ai_score", 0)
            risk_level = ai_result.get("risk_level", "safe")

            saved_flag = self.submission_repo.save_ai_flag(
                submission_id=submission.id,
                confidence_score=ai_score,
                risk_level=risk_level,
                flag_type="AI_METADATA",
                status="pending"
            )

            self.submission_repo.save_ai_analysis_report(
                submission_id=submission.id,
                ai_flag_id=saved_flag.id,
                ai_model_name="EXIF Extraction Engine",
                ai_confidence_score=ai_score,
                raw_details={
                    "exif_data": ai_result.get("exif_data", {}),
                    "raw_exif": ai_result.get("raw_exif", {})
                }
            )
        except Exception:
            pass

        return submission

    def get_submission_by_id(
        self,
        submission_id: int,
    ) -> Optional[
        Tuple[
            SubmissionModel,
            Optional[SubmissionFileModel],
            Optional[
                SubmissionFilmMetadataModel
            ],
        ]
    ]:

        return (
            self.submission_repo
            .get_by_id_with_details(
                submission_id
            )
        )

    def list_submissions(self):
        return self.submission_repo.list()