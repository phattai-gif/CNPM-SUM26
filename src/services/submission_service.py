import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from infrastructure.repositories.submission_repository import (
    SubmissionRepository,
)

from services.storage_service import StorageService

from infrastructure.models.app import (
    SubmissionModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
    AIFlagModel,
    ContestModel,
    JudgeAssignmentModel,
)


class SubmissionService:
    """
    Application Service for Submission workflows.

    Supported submission files:

    - main_image
    - negative_film
    - contact_sheet

    The service handles:

    - Image upload
    - Proof file upload
    - Storage processing
    - Submission creation
    - Draft update
    - Draft submission
    - Submission detail retrieval
    - Submission listing
    - AI detection
    - Duplicate image detection
    """

    # =========================================================
    # CONSTANTS
    # =========================================================

    ALLOWED_FILE_TYPES = {
        "main_image",
        "negative",
        "negative_film",
        "contact_sheet",
    }

    DEFAULT_FILE_TYPE = "main_image"

    # =========================================================
    # INIT
    # =========================================================

    def __init__(
        self,
        submission_repo: Optional[SubmissionRepository] = None,
        storage_service: Optional[StorageService] = None,
    ):
        self.submission_repo = (
            submission_repo
            or SubmissionRepository()
        )

        self.storage_service = (
            storage_service
            or StorageService()
        )

    # =========================================================
    # FILE TYPE HELPERS
    # =========================================================

    def _normalize_file_type(
        self,
        file_type: Optional[str],
    ) -> str:
        """
        Normalize and validate submission file type.
        """

        if file_type is None:
            return self.DEFAULT_FILE_TYPE

        normalized = str(
            file_type
        ).strip().lower()

        if normalized not in self.ALLOWED_FILE_TYPES:
            raise ValueError(
                "Invalid file_type. "
                "Allowed values: "
                "main_image, negative, "
                "negative_film, contact_sheet"
            )

        return normalized

    def _normalize_file_item(
        self,
        file_item: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize one uploaded file item.
        """

        if not isinstance(
            file_item,
            dict,
        ):
            raise ValueError(
                "Each file must be an object"
            )

        file_type = self._normalize_file_type(
            file_item.get(
                "file_type"
            )
        )

        return {
            "file_bytes": file_item.get(
                "file_bytes"
            ),
            "filename": file_item.get(
                "filename"
            ),
            "content_type": (
                file_item.get(
                    "content_type"
                )
                or "image/jpeg"
            ),
            "file_type": file_type,
        }

    def _validate_file_type(
        self,
        file_type: Optional[str],
    ) -> str:
        """
        Public-style validation helper used internally.
        """

        return self._normalize_file_type(
            file_type
        )

    # =========================================================
    # HASH HELPERS
    # =========================================================

    def _calculate_image_hashes(
        self,
        file_bytes: bytes,
    ) -> Tuple[
        Optional[str],
        Optional[str],
    ]:
        """
        Calculate perceptual hashes.

        Returns:
            (phash, ahash)
        """

        if not file_bytes:
            return None, None

        # -----------------------------------------------------
        # Preferred duplicate detection service
        # -----------------------------------------------------

        try:
            from services.duplicate_detection_service import (
                DuplicateDetectionService,
            )

            dup_service = (
                DuplicateDetectionService()
            )

            phash = None
            ahash = None

            if hasattr(
                dup_service,
                "calculate_phash_from_bytes",
            ):
                phash = (
                    dup_service
                    .calculate_phash_from_bytes(
                        file_bytes
                    )
                )

            if hasattr(
                dup_service,
                "calculate_ahash_from_bytes",
            ):
                ahash = (
                    dup_service
                    .calculate_ahash_from_bytes(
                        file_bytes
                    )
                )

            if (
                phash is not None
                and ahash is not None
            ):
                return (
                    str(phash),
                    str(ahash),
                )

        except Exception:
            pass

        # -----------------------------------------------------
        # PIL + imagehash fallback
        # -----------------------------------------------------

        try:
            from PIL import Image
            import imagehash

            image = Image.open(
                BytesIO(file_bytes)
            )

            phash = imagehash.phash(
                image
            )

            ahash = imagehash.average_hash(
                image
            )

            return (
                str(phash),
                str(ahash),
            )

        except Exception:
            return None, None

    # =========================================================
    # STORAGE
    # =========================================================

    def upload_submission_image(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Upload one submission image.
        """

        return self.storage_service.upload_image(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

    # =========================================================
    # BUILD FILE DATA
    # =========================================================

    def _upload_file_item(
        self,
        file_item: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Upload one file and convert it to repository format.
        """

        normalized = self._normalize_file_item(
            file_item
        )

        file_bytes = normalized[
            "file_bytes"
        ]

        filename = normalized[
            "filename"
        ]

        content_type = normalized[
            "content_type"
        ]

        file_type = normalized[
            "file_type"
        ]

        if not file_bytes:
            raise ValueError(
                "file_bytes is required"
            )

        if not filename:
            raise ValueError(
                "filename is required"
            )

        # -----------------------------------------------------
        # Upload
        # -----------------------------------------------------

        storage_info = (
            self.storage_service.upload_image(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
        )

        if not isinstance(
            storage_info,
            dict,
        ):
            raise ValueError(
                "Invalid storage response"
            )

        # -----------------------------------------------------
        # Hash
        # -----------------------------------------------------

        phash_val, ahash_val = (
            self._calculate_image_hashes(
                file_bytes
            )
        )

        # -----------------------------------------------------
        # Return repository data
        # -----------------------------------------------------

        return {
            "file_type": file_type,
            "image_hd_url": storage_info.get(
                "hd_url"
            ),
            "thumbnail_url": storage_info.get(
                "thumbnail_url"
            ),
            "file_hash": storage_info.get(
                "sha256"
            ),
            "width_px": storage_info.get(
                "width"
            ),
            "height_px": storage_info.get(
                "height"
            ),
            "file_size_bytes": storage_info.get(
                "file_size"
            ),
            "phash": phash_val,
            "ahash": ahash_val,
        }

    def _build_files_data(
        self,
        files: Optional[
            List[Dict[str, Any]]
        ],
    ) -> List[Dict[str, Any]]:

        if not files:
            return []

        files_data = []

        for file_item in files:

            if not isinstance(
                file_item,
                dict,
            ):
                raise ValueError(
                    "Invalid file item"
                )

            normalized = (
                self._normalize_file_item(
                    file_item
                )
            )

            if (
                not normalized[
                    "file_bytes"
                ]
                or not normalized[
                    "filename"
                ]
            ):
                continue

            files_data.append(
                self._upload_file_item(
                    normalized
                )
            )

        return files_data

    # =========================================================
    # CREATE SUBMISSION
    # =========================================================

    def create_submission(
        self,
        round_id: int,
        user_id: int,
        title: str,
        files: Optional[
            List[Dict[str, Any]]
        ] = None,
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
        file_type: Optional[str] = None,
    ) -> SubmissionModel:

        film_metadata = (
            film_metadata or {}
        )

        files_data: List[
            Dict[str, Any]
        ] = []

        # =====================================================
        # MULTIPLE FILES
        # =====================================================

        if files:

            files_data = (
                self._build_files_data(
                    files
                )
            )

        # =====================================================
        # SINGLE FILE
        # =====================================================

        elif (
            file_bytes
            and len(file_bytes) > 0
            and filename
        ):

            normalized_file_type = (
                self._normalize_file_type(
                    file_type
                )
            )

            files_data.append(
                self._upload_file_item(
                    {
                        "file_bytes": file_bytes,
                        "filename": filename,
                        "content_type": (
                            content_type
                            or "image/jpeg"
                        ),
                        "file_type": (
                            normalized_file_type
                        ),
                    }
                )
            )

        # =====================================================
        # EXISTING FILE
        # =====================================================

        elif image_hd_url and file_hash:

            normalized_file_type = (
                self._normalize_file_type(
                    file_type
                )
            )

            files_data.append(
                {
                    "file_type": (
                        normalized_file_type
                    ),
                    "image_hd_url": (
                        image_hd_url
                    ),
                    "thumbnail_url": (
                        thumbnail_url
                    ),
                    "file_hash": file_hash,
                    "width_px": width_px,
                    "height_px": height_px,
                    "file_size_bytes": (
                        file_size_bytes
                    ),
                    "phash": None,
                    "ahash": None,
                }
            )

        # =====================================================
        # VALIDATE SUBMISSION
        # =====================================================

        if status != "draft":

            if not files_data:
                raise ValueError(
                    "At least one image file is required"
                )

            if not film_metadata.get(
                "film_stock"
            ):
                raise ValueError(
                    "film_metadata.film_stock is required"
                )

        # =====================================================
        # FIND MAIN IMAGE
        # =====================================================

        main_image = None

        for file_data in files_data:

            if (
                file_data.get(
                    "file_type"
                )
                == "main_image"
            ):
                main_image = file_data
                break

        # Backward compatibility:
        # if no explicit main_image exists,
        # use first file.
        if (
            main_image is None
            and files_data
        ):
            main_image = files_data[0]

        first_file = (
            main_image
            if main_image
            else {}
        )

        # =====================================================
        # CREATE SUBMISSION
        # =====================================================

        submission = (
            self.submission_repo
            .create_submission(
                round_id=round_id,
                user_id=user_id,
                title=title,
                image_hd_url=(
                    first_file.get(
                        "image_hd_url"
                    )
                ),
                file_hash=(
                    first_file.get(
                        "file_hash"
                    )
                ),
                thumbnail_url=(
                    first_file.get(
                        "thumbnail_url"
                    )
                ),
                width_px=(
                    first_file.get(
                        "width_px"
                    )
                ),
                height_px=(
                    first_file.get(
                        "height_px"
                    )
                ),
                file_size_bytes=(
                    first_file.get(
                        "file_size_bytes"
                    )
                ),
                files_data=files_data,
                story_description=(
                    story_description
                ),
                film_stock=(
                    film_metadata.get(
                        "film_stock"
                    )
                    or ""
                ),
                film_iso=(
                    film_metadata.get(
                        "film_iso"
                    )
                ),
                camera_body=(
                    film_metadata.get(
                        "camera_body"
                    )
                ),
                lens=(
                    film_metadata.get(
                        "lens"
                    )
                ),
                lab_name=(
                    film_metadata.get(
                        "lab_name"
                    )
                ),
                scanner_info=(
                    film_metadata.get(
                        "scanner_info"
                    )
                ),
                development_process=(
                    film_metadata.get(
                        "development_process"
                    )
                    or "C-41"
                ),
                taken_at_location=(
                    film_metadata.get(
                        "taken_at_location"
                    )
                ),
                status=status,
            )
        )

        # =====================================================
        # AI DETECTION
        # =====================================================

        if (
            first_file.get(
                "image_hd_url"
            )
            and status != "draft"
        ):

            self._run_ai_detection(
                submission=submission,
                image_url=first_file.get(
                    "image_hd_url"
                ),
                film_metadata=film_metadata,
            )

        # =====================================================
        # DUPLICATE DETECTION
        # =====================================================

        try:

            first_bytes = None

            if files:
                for file_item in files:

                    if (
                        self._normalize_file_type(
                            file_item.get(
                                "file_type"
                            )
                        )
                        == "main_image"
                    ):
                        first_bytes = (
                            file_item.get(
                                "file_bytes"
                            )
                        )
                        break

                if (
                    first_bytes is None
                    and files
                ):
                    first_bytes = (
                        files[0].get(
                            "file_bytes"
                        )
                    )

            elif file_bytes:
                first_bytes = file_bytes

            if (
                first_bytes
                and status != "draft"
            ):
                self._run_duplicate_check_and_flag(
                    submission,
                    first_bytes,
                )

        except Exception as e:
            print(
                f"Warning: duplicate check failed: {e}"
            )

        return submission

    # =========================================================
    # AI DETECTION
    # =========================================================

    def _run_ai_detection(
        self,
        submission: SubmissionModel,
        image_url: str,
        film_metadata: Dict[str, Any],
    ) -> None:

        try:

            from services.ai_detection_service import (
                AiDetectionService,
            )

            ai_service = (
                AiDetectionService()
            )

            ai_result = (
                ai_service.detect_ai(
                    image_url
                )
            )

            if not isinstance(
                ai_result,
                dict,
            ):
                ai_result = {}

            ai_score = ai_result.get(
                "ai_score",
                0,
            )

            comparison_result = (
                ai_service
                .compare_metadata_with_exif(
                    film_metadata,
                    ai_result.get(
                        "exif_data",
                        {},
                    ),
                )
            )

            if not isinstance(
                comparison_result,
                dict,
            ):
                comparison_result = {}

            ai_score = max(
                float(
                    ai_result.get(
                        "ai_score",
                        0,
                    )
                    or 0
                ),
                float(
                    comparison_result.get(
                        "confidence_score",
                        0,
                    )
                    or 0
                ),
            )

            base_risk = ai_result.get(
                "risk_level",
                "safe",
            )

            comp_risk = (
                comparison_result.get(
                    "risk_level",
                    "safe",
                )
            )

            if "high" in [
                base_risk,
                comp_risk,
            ]:
                risk_level = "high"

            elif "medium" in [
                base_risk,
                comp_risk,
            ]:
                risk_level = "medium"

            else:
                risk_level = "safe"

            saved_flag = (
                self.submission_repo
                .save_ai_flag(
                    submission_id=submission.id,
                    confidence_score=ai_score,
                    risk_level=risk_level,
                    flag_type="AI_METADATA",
                    status="pending",
                )
            )

            self.submission_repo.save_ai_analysis_report(
                submission_id=submission.id,
                ai_flag_id=saved_flag.id,
                ai_model_name=(
                    "EXIF Extraction Engine"
                ),
                ai_confidence_score=ai_score,
                raw_details={
                    "exif_data": (
                        ai_result.get(
                            "exif_data",
                            {},
                        )
                    ),
                    "raw_exif": (
                        ai_result.get(
                            "raw_exif",
                            {},
                        )
                    ),
                    "metadata_comparison": (
                        comparison_result
                    ),
                },
            )

        except Exception as e:
            print(
                f"Warning: AI detection failed: {e}"
            )

    # =========================================================
    # UPDATE DRAFT
    # =========================================================

    def update_draft(
        self,
        submission_id: int,
        user_id: int,
        title: Optional[str] = None,
        story_description: Optional[str] = None,
        files: Optional[
            List[Dict[str, Any]]
        ] = None,
        film_metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> SubmissionModel:

        submission = (
            self.submission_repo
            .get_by_id(
                submission_id
            )
        )

        if not submission:
            raise ValueError(
                "Submission not found"
            )

        if submission.user_id != user_id:
            raise PermissionError(
                "Forbidden"
            )

        if submission.status != "draft":
            raise ValueError(
                "Cannot edit submission that is not in draft status"
            )

        files_data = None

        if files:
            files_data = (
                self._build_files_data(
                    files
                )
            )

        return (
            self.submission_repo
            .update_draft(
                submission_id=submission_id,
                user_id=user_id,
                title=title,
                story_description=(
                    story_description
                ),
                files_data=files_data,
                film_metadata=(
                    film_metadata
                ),
            )
        )

    def update_draft_submission(self, *args, **kwargs):
        return self.update_draft(*args, **kwargs)

    # =========================================================
    # SUBMIT DRAFT
    # =========================================================

    def submit_draft(
        self,
        submission_id: int,
        user_id: int,
    ) -> SubmissionModel:

        result = (
            self.submission_repo
            .get_by_id_with_details(
                submission_id
            )
        )

        if not result:
            raise ValueError(
                "Submission not found"
            )

        (
            submission,
            submission_file,
            film_metadata,
        ) = result

        if submission.user_id != user_id:
            raise PermissionError(
                "Forbidden"
            )

        if submission.status != "draft":
            raise ValueError(
                "Cannot submit submission that is not in draft status"
            )

        if (
            not submission.title
            or not submission.title.strip()
        ):
            raise ValueError(
                "title is required"
            )

        if not submission_file:
            raise ValueError(
                "At least one image file is required"
            )

        if (
            not film_metadata
            or not film_metadata.film_stock
            or not film_metadata.film_stock.strip()
        ):
            raise ValueError(
                "film_stock is required"
            )

        now_utc = datetime.now(
            timezone.utc
        )

        updated_submission = (
            self.submission_repo
            .update_status(
                submission_id=submission_id,
                status="submitted",
                submitted_at=now_utc,
            )
        )

        # -----------------------------------------------------
        # AI
        # -----------------------------------------------------

        image_url = getattr(
            submission_file,
            "image_hd_url",
            None,
        )

        if image_url:

            self._run_ai_detection(
                submission=submission,
                image_url=image_url,
                film_metadata={
                    "film_stock": (
                        getattr(
                            film_metadata,
                            "film_stock",
                            None,
                        )
                    ),
                    "film_iso": (
                        getattr(
                            film_metadata,
                            "film_iso",
                            None,
                        )
                    ),
                    "camera_body": (
                        getattr(
                            film_metadata,
                            "camera_body",
                            None,
                        )
                    ),
                    "lens": (
                        getattr(
                            film_metadata,
                            "lens",
                            None,
                        )
                    ),
                    "lab_name": (
                        getattr(
                            film_metadata,
                            "lab_name",
                            None,
                        )
                    ),
                },
            )

        # -----------------------------------------------------
        # Duplicate detection
        # -----------------------------------------------------

        try:

            local_path = image_url

            if (
                local_path.startswith(
                    "http://"
                )
                or local_path.startswith(
                    "https://"
                )
                or local_path.startswith(
                    "/static/uploads/"
                )
            ):

                if "/static/uploads/" in local_path:

                    filename = (
                        local_path.split(
                            "/static/uploads/"
                        )[-1]
                    )

                    project_root = (
                        os.path.abspath(
                            os.path.join(
                                os.path.dirname(
                                    __file__
                                ),
                                "../..",
                            )
                        )
                    )

                    local_path = os.path.join(
                        project_root,
                        "frontend",
                        "static",
                        "uploads",
                        filename,
                    )

                else:

                    try:
                        import urllib.request
                        import tempfile

                        suffix = (
                            os.path.splitext(
                                local_path.split(
                                    "?"
                                )[0]
                            )[1]
                            .lower()
                            or ".jpg"
                        )

                        temp_file = (
                            tempfile.NamedTemporaryFile(
                                delete=False,
                                suffix=suffix,
                            )
                        )

                        temp_file.close()

                        urllib.request.urlretrieve(
                            image_url,
                            temp_file.name,
                        )

                        local_path = (
                            temp_file.name
                        )

                    except Exception:
                        pass

            if os.path.exists(
                local_path
            ):

                with open(
                    local_path,
                    "rb",
                ) as f:
                    file_data = f.read()

                phash_val, ahash_val = (
                    self._calculate_image_hashes(
                        file_data
                    )
                )

                if (
                    phash_val is not None
                    or ahash_val is not None
                ):

                    if hasattr(
                        submission_file,
                        "phash",
                    ):
                        submission_file.phash = (
                            phash_val
                        )

                    if hasattr(
                        submission_file,
                        "ahash",
                    ):
                        submission_file.ahash = (
                            ahash_val
                        )

                    self.submission_repo.session.commit()

                self._run_duplicate_check_and_flag(
                    updated_submission,
                    file_data,
                )

        except Exception as e:
            print(
                f"Warning: duplicate check failed: {e}"
            )

        return updated_submission

    # =========================================================
    # GET SUBMISSION BY ID
    # =========================================================

    def get_submission_by_id(
        self,
        submission_id: int,
    ):

        return (
            self.submission_repo
            .get_by_id_with_details(
                submission_id
            )
        )


    def list_submissions(self):
        return self.submission_repo.list()

    # =========================================================
    # GET SUBMISSION DETAIL
    # =========================================================

    def get_submission_detail(
        self,
        submission_id: int,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:

        result = (
            self.submission_repo
            .get_by_id_with_details(
                submission_id
            )
        )

        if not result:
            return None

        submission = result[0]

        # -----------------------------------------------------
        # GET ALL SUBMISSION FILES
        # -----------------------------------------------------

        submission_files = []

        existing_files = getattr(
            submission,
            "files",
            None,
        )

        if existing_files:
            if isinstance(
                existing_files,
                (list, tuple),
            ):
                submission_files = list(
                    existing_files
                )
            else:
                submission_files = [
                    existing_files
                ]

        # -----------------------------------------------------
        # FALLBACK FILE FROM REPOSITORY
        # -----------------------------------------------------

        if (
            not submission_files
            and len(result) > 1
        ):
            submission_file = result[1]

            if isinstance(
                submission_file,
                (list, tuple),
            ):
                submission_files = list(
                    submission_file
                )

            elif submission_file:
                submission_files = [
                    submission_file
                ]

        # -----------------------------------------------------
        # FILM METADATA
        # -----------------------------------------------------

        film_metadata = (
            result[2]
            if len(result) > 2
            else None
        )

        # -----------------------------------------------------
        # AI FLAGS
        # -----------------------------------------------------

        ai_flags = (
            self.submission_repo
            .get_all_ai_flags(
                submission_id
            )
        )

        # -----------------------------------------------------
        # FORMAT SUBMISSION
        # -----------------------------------------------------

        data = self._format_submission_dict(
            submission,
            submission_files,
            film_metadata,
            ai_flags,
        )

        # -----------------------------------------------------
        # ENSURE ALL FILES ARE RETURNED
        # -----------------------------------------------------

        if not isinstance(data, dict):
            data = {}

        data["files"] = submission_files

        # -----------------------------------------------------
        # PARTICIPANT PERMISSION
        # -----------------------------------------------------

        if (
            role == "participant"
            and user_id is not None
        ):
            if (
                data.get("user_id")
                != user_id
            ):
                raise PermissionError(
                    "Access forbidden: "
                    "You can only view your own submission details."
                )

        return data

    # =========================================================
    # UPDATE DRAFT SUBMISSION
    # =========================================================

    def update_draft_submission(
        self,
        submission_id: int,
        user_id: int,
        title: Optional[str] = None,
        story_description: Optional[str] = None,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        film_metadata: Optional[
            Dict[str, Any]
        ] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = "image/jpeg",
        image_hd_url: Optional[str] = None,
        file_hash: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        width_px: Optional[int] = None,
        height_px: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        file_type: Optional[str] = None,
    ) -> SubmissionModel:

        if (
            file_bytes
            and len(file_bytes) > 0
            and filename
        ):

            normalized_file_type = (
                self._normalize_file_type(
                    file_type
                )
            )

            storage_info = (
                self.storage_service
                .upload_image(
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=(
                        content_type
                        or "image/jpeg"
                    ),
                )
            )

            image_hd_url = (
                storage_info.get(
                    "hd_url"
                )
            )

            thumbnail_url = (
                storage_info.get(
                    "thumbnail_url"
                )
            )

            file_hash = (
                storage_info.get(
                    "sha256"
                )
            )

            width_px = (
                storage_info.get(
                    "width"
                )
            )

            height_px = (
                storage_info.get(
                    "height"
                )
            )

            file_size_bytes = (
                storage_info.get(
                    "file_size"
                )
            )

        else:
            normalized_file_type = (
                self._normalize_file_type(
                    file_type
                )
            )

        # -----------------------------------------------------
        # Update repository
        # -----------------------------------------------------

        try:

            submission = (
                self.submission_repo
                .update_draft_submission(
                    submission_id=submission_id,
                    user_id=user_id,
                    title=title,
                    story_description=(
                        story_description
                    ),
                    round_id=round_id,
                    status=status,
                    film_metadata=(
                        film_metadata
                    ),
                    image_hd_url=(
                        image_hd_url
                    ),
                    thumbnail_url=(
                        thumbnail_url
                    ),
                    file_hash=(
                        file_hash
                    ),
                    width_px=(
                        width_px
                    ),
                    height_px=(
                        height_px
                    ),
                    file_size_bytes=(
                        file_size_bytes
                    ),
                    file_type=(
                        normalized_file_type
                    ),
                )
            )

        except TypeError:
            # Backward compatibility with an older repository
            # that does not yet accept file_type.
            submission = (
                self.submission_repo
                .update_draft_submission(
                    submission_id=submission_id,
                    user_id=user_id,
                    title=title,
                    story_description=(
                        story_description
                    ),
                    round_id=round_id,
                    status=status,
                    film_metadata=(
                        film_metadata
                    ),
                    image_hd_url=(
                        image_hd_url
                    ),
                    thumbnail_url=(
                        thumbnail_url
                    ),
                    file_hash=(
                        file_hash
                    ),
                    width_px=(
                        width_px
                    ),
                    height_px=(
                        height_px
                    ),
                    file_size_bytes=(
                        file_size_bytes
                    ),
                )
            )

        # -----------------------------------------------------
        # AI detection
        # -----------------------------------------------------

        if (
            status == "submitted"
            and image_hd_url
        ):

            self._run_ai_detection(
                submission=submission,
                image_url=image_hd_url,
                film_metadata=(
                    film_metadata
                    or {}
                ),
            )

        return submission

    # =========================================================
    # LIST SUBMISSIONS
    # =========================================================

    def list_submissions(
        self,
    ):

        return (
            self.submission_repo
            .list()
        )

    # =========================================================
    # DUPLICATE DETECTION
    # =========================================================

    def _run_duplicate_check_and_flag(
        self,
        submission,
        file_bytes: bytes,
    ):
        """
        Duplicate detection must never block
        submission creation.
        """

        try:

            from services.duplicate_detection_service import (
                DuplicateDetectionService,
            )

            dup_service = (
                DuplicateDetectionService()
            )

            dup_result = (
                dup_service
                .check_duplicate_against_database(
                    new_image_bytes=file_bytes,
                    exclude_submission_id=(
                        submission.id
                    ),
                    session=(
                        self.submission_repo
                        .session
                    ),
                )
            )

            if not isinstance(
                dup_result,
                dict,
            ):
                dup_result = {}

            similarity = float(
                dup_result.get(
                    "similarity_score",
                    0.0,
                )
                or 0.0
            )

            is_duplicate = bool(
                dup_result.get(
                    "is_duplicate",
                    False,
                )
            )

            if is_duplicate:
                risk_level = "high"
                flag_status = "pending"

            elif similarity >= 70.0:
                risk_level = "medium"
                flag_status = "pending"

            else:
                risk_level = "safe"
                flag_status = "clear"

            saved_flag = (
                self.submission_repo
                .save_ai_flag(
                    submission_id=submission.id,
                    confidence_score=similarity,
                    risk_level=risk_level,
                    flag_type=(
                        "duplicate_similarity"
                    ),
                    status=flag_status,
                )
            )

            matched_sub_id = (
                dup_result.get(
                    "matched_submission_id"
                )
            )

            try:

                self.submission_repo.save_ai_analysis_report(
                    submission_id=submission.id,
                    ai_flag_id=saved_flag.id,
                    ai_model_name=(
                        "Duplicate Detection Engine"
                    ),
                    ai_confidence_score=similarity,
                    raw_details=dup_result,
                    similarity_matched_submission_id=(
                        matched_sub_id
                    ),
                )

            except TypeError:

                self.submission_repo.save_ai_analysis_report(
                    submission_id=submission.id,
                    ai_flag_id=saved_flag.id,
                    ai_model_name=(
                        "Duplicate Detection Engine"
                    ),
                    ai_confidence_score=similarity,
                    raw_details=dup_result,
                )

        except Exception as e:

            print(
                f"Warning: duplicate check failed: {e}"
            )

    # =========================================================
    # FORMAT ONE FILE
    # =========================================================

    def _format_file_dict(
        self,
        submission_file: Any,
    ) -> Dict[str, Any]:
        """
        Convert SubmissionFileModel to API response.
        """

        if isinstance(
            submission_file,
            dict,
        ):
            file_type = (
                submission_file.get(
                    "file_type"
                )
                or self.DEFAULT_FILE_TYPE
            )

            created_at = (
                submission_file.get(
                    "created_at"
                )
            )

            if hasattr(
                created_at,
                "isoformat",
            ):
                created_at = (
                    created_at.isoformat()
                )

            return {
                "id": submission_file.get(
                    "id"
                ),
                "file_type": file_type,
                "image_hd_url": (
                    submission_file.get(
                        "image_hd_url"
                    )
                ),
                "thumbnail_url": (
                    submission_file.get(
                        "thumbnail_url"
                    )
                ),
                "width_px": (
                    submission_file.get(
                        "width_px"
                    )
                ),
                "height_px": (
                    submission_file.get(
                        "height_px"
                    )
                ),
                "file_size_bytes": (
                    submission_file.get(
                        "file_size_bytes"
                    )
                ),
                "file_hash": (
                    submission_file.get(
                        "file_hash"
                    )
                ),
                "phash": (
                    submission_file.get(
                        "phash"
                    )
                ),
                "ahash": (
                    submission_file.get(
                        "ahash"
                    )
                ),
                "created_at": created_at,
            }

        file_type = getattr(
            submission_file,
            "file_type",
            None,
        )

        if not file_type:
            file_type = (
                self.DEFAULT_FILE_TYPE
            )

        created_at = getattr(
            submission_file,
            "created_at",
            None,
        )

        return {
            "id": getattr(
                submission_file,
                "id",
                None,
            ),
            "file_type": file_type,
            "image_hd_url": getattr(
                submission_file,
                "image_hd_url",
                None,
            ),
            "thumbnail_url": getattr(
                submission_file,
                "thumbnail_url",
                None,
            ),
            "width_px": getattr(
                submission_file,
                "width_px",
                None,
            ),
            "height_px": getattr(
                submission_file,
                "height_px",
                None,
            ),
            "file_size_bytes": getattr(
                submission_file,
                "file_size_bytes",
                None,
            ),
            "file_hash": getattr(
                submission_file,
                "file_hash",
                None,
            ),
            "phash": getattr(
                submission_file,
                "phash",
                None,
            ),
            "ahash": getattr(
                submission_file,
                "ahash",
                None,
            ),
            "created_at": (
                created_at.isoformat()
                if created_at
                else None
            ),
        }

    # =========================================================
    # FORMAT FILM METADATA
    # =========================================================

    def _format_film_metadata(
        self,
        film_metadata,
    ) -> Optional[Dict[str, Any]]:

        if not film_metadata:
            return None

        created_at = getattr(
            film_metadata,
            "created_at",
            None,
        )

        return {
            "film_stock": getattr(
                film_metadata,
                "film_stock",
                None,
            ),
            "film_iso": getattr(
                film_metadata,
                "film_iso",
                None,
            ),
            "camera_body": getattr(
                film_metadata,
                "camera_body",
                None,
            ),
            "lens": getattr(
                film_metadata,
                "lens",
                None,
            ),
            "lab_name": getattr(
                film_metadata,
                "lab_name",
                None,
            ),
            "scanner_info": getattr(
                film_metadata,
                "scanner_info",
                None,
            ),
            "development_process": getattr(
                film_metadata,
                "development_process",
                None,
            ),
            "taken_at_location": getattr(
                film_metadata,
                "taken_at_location",
                None,
            ),
            "created_at": (
                created_at.isoformat()
                if created_at
                else None
            ),
        }

    # =========================================================
    # FORMAT SUBMISSION
    # =========================================================

    def _format_submission_dict(
        self,
        submission: SubmissionModel,
        submission_file: Any = None,
        film_metadata: Optional[
            SubmissionFilmMetadataModel
        ] = None,
        ai_flags: Optional[
            List[AIFlagModel]
        ] = None,
    ) -> Dict[str, Any]:

        item = {
            "id": submission.id,
            "round_id": submission.round_id,
            "user_id": submission.user_id,
            "title": submission.title,
            "story_description": (
                submission.story_description
            ),
            "status": submission.status,
            "final_score": (
                float(
                    submission.final_score
                )
                if submission.final_score
                is not None
                else None
            ),
            "submitted_at": (
                submission.submitted_at.isoformat()
                if submission.submitted_at
                else None
            ),
            "created_at": (
                submission.created_at.isoformat()
                if submission.created_at
                else None
            ),
            "updated_at": (
                submission.updated_at.isoformat()
                if submission.updated_at
                else None
            ),
            "file": None,
            "proof_files": [],
            "film_metadata": (
                self._format_film_metadata(
                    film_metadata
                )
            ),
            "ai_flags": [],
        }

        # =====================================================
        # FILES
        # =====================================================

        file_objects = []

        if submission_file:

            if isinstance(
                submission_file,
                (list, tuple, set),
            ):
                file_objects = list(
                    submission_file
                )

            else:
                file_objects = [
                    submission_file
                ]

        formatted_files = [
            self._format_file_dict(
                file_obj
            )
            for file_obj in file_objects
            if file_obj
        ]

        # -----------------------------------------------------
        # Main image
        # -----------------------------------------------------

        main_file = None

        for file_obj in formatted_files:

            if (
                file_obj.get(
                    "file_type"
                )
                == "main_image"
            ):
                main_file = file_obj
                break

        # Backward compatibility
        if (
            main_file is None
            and formatted_files
        ):
            main_file = formatted_files[0]

        item["file"] = main_file

        # -----------------------------------------------------
        # Proof files
        # -----------------------------------------------------

        item["proof_files"] = [
            file_obj
            for file_obj in formatted_files
            if file_obj != "main_image"
        ]

        # -----------------------------------------------------
        # AI flags
        # -----------------------------------------------------

        if ai_flags:

            item["ai_flags"] = [
                {
                    "id": flag.id,
                    "flag_type": flag.flag_type,
                    "ai_score": (
                        float(
                            flag.confidence_score
                        )
                        if flag.confidence_score
                        is not None
                        else None
                    ),
                    "risk_level": (
                        flag.risk_level
                    ),
                    "status": flag.status,
                }
                for flag in ai_flags
            ]

        return item

    # =========================================================
    # MY SUBMISSIONS
    # =========================================================

    def get_my_submissions(
        self,
        user_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ) -> Dict[str, Any]:

        rows = (
            self.submission_repo
            .get_participant_submissions(
                user_id=user_id,
                round_id=round_id,
                status=status,
                ai_flag=ai_flag,
            )
        )

        submissions = []

        for row in rows:

            (
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            ) = row

            submissions.append(
                self._format_submission_dict(
                    sub,
                    file_obj,
                    meta_obj,
                    ai_obj,
                )
            )

        return {
            "submissions": submissions,
            "total": len(submissions),
        }

    # =========================================================
    # ORGANIZER SUBMISSIONS
    # =========================================================

    def get_organizer_submissions(
        self,
        contest_id: int,
        user_id: int,
        user_role: str,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ) -> Dict[str, Any]:

        contest = (
            self.submission_repo
            .session
            .query(ContestModel)
            .filter_by(
                id=contest_id
            )
            .first()
        )

        if not contest:
            raise ValueError(
                "Contest not found"
            )

        if (
            user_role != "admin"
            and contest.created_by != user_id
        ):
            raise PermissionError(
                "Forbidden"
            )

        rows = (
            self.submission_repo
            .get_organizer_submissions(
                contest_id=contest_id,
                round_id=round_id,
                status=status,
                ai_flag=ai_flag,
            )
        )

        submissions = []

        for row in rows:

            (
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            ) = row

            submissions.append(
                self._format_submission_dict(
                    sub,
                    file_obj,
                    meta_obj,
                    ai_obj,
                )
            )

        return {
            "submissions": submissions,
            "total": len(submissions),
        }

    # =========================================================
    # JUDGE ASSIGNMENT SUBMISSIONS
    # =========================================================

    def get_judge_assignment_submissions(
        self,
        assignment_id: int,
        user_id: int,
        user_role: str,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ) -> Dict[str, Any]:

        assignment = (
            self.submission_repo
            .session
            .query(JudgeAssignmentModel)
            .filter_by(
                id=assignment_id
            )
            .first()
        )

        if not assignment:
            raise ValueError(
                "Assignment not found"
            )

        if (
            user_role != "admin"
            and assignment.judge_id != user_id
        ):
            raise PermissionError(
                "Forbidden"
            )

        rows = (
            self.submission_repo
            .get_judge_assignment_submissions(
                assignment_id=assignment_id,
                round_id=round_id,
                status=status,
                ai_flag=ai_flag,
            )
        )

        if rows is None:
            raise ValueError(
                "Assignment not found"
            )

        submissions = []

        for row in rows:

            (
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            ) = row

            submissions.append(
                self._format_submission_dict(
                    sub,
                    file_obj,
                    meta_obj,
                    ai_obj,
                )
            )

        return {
            "submissions": submissions,
            "total": len(submissions),
        }

    # =========================================================
    # MODERATOR DASHBOARD
    # =========================================================

    def get_flagged_submissions(
        self,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:

        rows = (
            self.submission_repo
            .get_flagged_submissions(
                status=status,
            )
        )

        submissions = []

        for row in rows:

            (
                sub,
                file_obj,
                meta_obj,
                ai_objs,
            ) = row

            submissions.append(
                self._format_submission_dict(
                    sub,
                    file_obj,
                    meta_obj,
                    ai_objs,
                )
            )

        return {
            "submissions": submissions,
            "total": len(submissions),
        }

    # =========================================================
    # UPDATE FLAG STATUS
    # =========================================================

    def update_flag_status(
        self,
        flag_id: int,
        status: str,
    ) -> Optional[Dict[str, Any]]:

        flag = (
            self.submission_repo
            .update_ai_flag_status(
                flag_id,
                status,
            )
        )

        if not flag:
            return None

        return {
            "id": flag.id,
            "flag_type": flag.flag_type,
            "ai_score": (
                float(
                    flag.confidence_score
                )
                if flag.confidence_score
                is not None
                else None
            ),
            "risk_level": flag.risk_level,
            "status": flag.status,
        }