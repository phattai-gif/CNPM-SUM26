import os

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

    Handles:
    - Image upload
    - Storage processing
    - Submission creation
    - Draft update
    - Draft submission
    - Submission detail retrieval
    - Submission listing
    - AI detection
    - Duplicate image detection
    """

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

    def _validate_round_status_for_submission(self, round_id: int):
        if not round_id:
            return
        session = getattr(self.submission_repo, "session", None)
        if session:
            try:
                from infrastructure.models.app import RoundModel
                round_obj = session.query(RoundModel).filter_by(id=round_id).first()
                if round_obj:
                    status_str = (round_obj.status or "").lower()
                    if status_str != "ongoing":
                        raise ValueError(f"Cannot submit to round with status '{round_obj.status}'")
            except ValueError:
                raise
            except Exception:
                pass

    # =========================================================
    # HASH HELPERS
    # =========================================================

    def _calculate_image_hashes(
        self,
        file_bytes: bytes,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Calculate perceptual hashes for an image.

        Returns:
            (phash, ahash)

        The DuplicateDetectionService is preferred because it is
        the project's existing duplicate-detection implementation.

        A local imagehash/PIL fallback is also provided so that
        submission creation can still calculate hashes when the
        duplicate service does not expose the expected methods.
        """

        if not file_bytes:
            return None, None

        # -----------------------------------------------------
        # Preferred implementation
        # -----------------------------------------------------

        try:
            from services.duplicate_detection_service import (
                DuplicateDetectionService,
            )

            dup_service = DuplicateDetectionService()

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

            phash = (
                str(phash)
                if phash is not None
                else None
            )

            ahash = (
                str(ahash)
                if ahash is not None
                else None
            )

            if phash is not None and ahash is not None:
                return phash, ahash

        except Exception:
            pass

        # -----------------------------------------------------
        # Fallback using PIL + imagehash
        # -----------------------------------------------------

        try:
            from io import BytesIO
            from PIL import Image
            import imagehash

            image = Image.open(
                BytesIO(file_bytes)
            )

            phash = imagehash.phash(image)
            ahash = imagehash.average_hash(image)

            return (
                str(phash),
                str(ahash),
            )

        except Exception:
            return None, None

    # =========================================================
    # UPLOAD IMAGE
    # =========================================================

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
    ) -> SubmissionModel:

        film_metadata = (
            film_metadata or {}
        )

        if status != "draft":
            self._validate_round_status_for_submission(round_id)

        files_data: List[
            Dict[str, Any]
        ] = []

        # =====================================================
        # UPLOAD MULTIPLE FILES
        # =====================================================

        if files:

            for file_item in files:

                file_bytes_item = (
                    file_item.get(
                        "file_bytes"
                    )
                )

                filename_item = (
                    file_item.get(
                        "filename"
                    )
                )

                content_type_item = (
                    file_item.get(
                        "content_type"
                    )
                    or "image/jpeg"
                )

                if (
                    not file_bytes_item
                    or not filename_item
                ):
                    continue

                # -------------------------------------------------
                # Upload image
                # -------------------------------------------------

                storage_info = (
                    self.storage_service
                    .upload_image(
                        file_bytes=file_bytes_item,
                        filename=filename_item,
                        content_type=content_type_item,
                    )
                )

                # -------------------------------------------------
                # Calculate perceptual hashes
                # -------------------------------------------------

                phash_val, ahash_val = (
                    self._calculate_image_hashes(
                        file_bytes_item
                    )
                )

                # -------------------------------------------------
                # Prepare file data
                # -------------------------------------------------

                files_data.append(
                    {
                        "image_hd_url": (
                            storage_info[
                                "hd_url"
                            ]
                        ),
                        "thumbnail_url": (
                            storage_info[
                                "thumbnail_url"
                            ]
                        ),
                        "file_hash": (
                            storage_info[
                                "sha256"
                            ]
                        ),
                        "width_px": (
                            storage_info[
                                "width"
                            ]
                        ),
                        "height_px": (
                            storage_info[
                                "height"
                            ]
                        ),
                        "file_size_bytes": (
                            storage_info[
                                "file_size"
                            ]
                        ),
                        "phash": phash_val,
                        "ahash": ahash_val,
                    }
                )

        # =====================================================
        # SINGLE FILE UPLOAD
        # =====================================================

        elif (
            file_bytes
            and len(file_bytes) > 0
            and filename
        ):

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

            phash_val, ahash_val = (
                self._calculate_image_hashes(
                    file_bytes
                )
            )

            files_data.append(
                {
                    "image_hd_url": (
                        storage_info[
                            "hd_url"
                        ]
                    ),
                    "thumbnail_url": (
                        storage_info[
                            "thumbnail_url"
                        ]
                    ),
                    "file_hash": (
                        storage_info[
                            "sha256"
                        ]
                    ),
                    "width_px": (
                        storage_info[
                            "width"
                        ]
                    ),
                    "height_px": (
                        storage_info[
                            "height"
                        ]
                    ),
                    "file_size_bytes": (
                        storage_info[
                            "file_size"
                        ]
                    ),
                    "phash": phash_val,
                    "ahash": ahash_val,
                }
            )

        # =====================================================
        # EXISTING FILE URL
        # =====================================================

        elif image_hd_url and file_hash:

            files_data.append(
                {
                    "image_hd_url": image_hd_url,
                    "thumbnail_url": thumbnail_url,
                    "file_hash": file_hash,
                    "width_px": width_px,
                    "height_px": height_px,
                    "file_size_bytes": file_size_bytes,
                    "phash": None,
                    "ahash": None,
                }
            )

        # =====================================================
        # VALIDATE OFFICIAL SUBMISSION
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
        # FIRST FILE
        # =====================================================

        first_file = (
            files_data[0]
            if files_data
            else {}
        )

        first_hd_url = first_file.get(
            "image_hd_url"
        )

        first_hash = first_file.get(
            "file_hash"
        )

        first_thumbnail_url = (
            first_file.get(
                "thumbnail_url"
            )
        )

        first_width = first_file.get(
            "width_px"
        )

        first_height = first_file.get(
            "height_px"
        )

        first_file_size = first_file.get(
            "file_size_bytes"
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
                    first_hd_url
                ),

                file_hash=(
                    first_hash
                ),

                thumbnail_url=(
                    first_thumbnail_url
                ),

                width_px=(
                    first_width
                ),

                height_px=(
                    first_height
                ),

                file_size_bytes=(
                    first_file_size
                ),

                files_data=(
                    files_data
                ),

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

        if first_hd_url:

            try:
                from services.ai_detection_service import (
                    AiDetectionService,
                )

                ai_service = (
                    AiDetectionService()
                )

                ai_result = (
                    ai_service.detect_ai(
                        first_hd_url
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
                    ai_result.get(
                        "ai_score",
                        0,
                    ),
                    comparison_result.get(
                        "confidence_score",
                        0,
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
                        submission_id=(
                            submission.id
                        ),
                        confidence_score=(
                            ai_score
                        ),
                        risk_level=(
                            risk_level
                        ),
                        flag_type=(
                            "AI_METADATA"
                        ),
                        status="pending",
                    )
                )

                self.submission_repo.save_ai_analysis_report(
                    submission_id=submission.id,
                    ai_flag_id=saved_flag.id,
                    ai_model_name=(
                        "EXIF Extraction Engine"
                    ),
                    ai_confidence_score=(
                        ai_score
                    ),
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

            except Exception:
                # AI is optional.
                # Never block submission creation.
                pass

        # =====================================================
        # DUPLICATE DETECTION
        # =====================================================

        try:

            first_bytes = None

            if files and len(files) > 0:
                first_bytes = files[0].get(
                    "file_bytes"
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

        files_data = []

        if files:

            for file_item in files:

                file_bytes_item = (
                    file_item.get(
                        "file_bytes"
                    )
                )

                filename_item = (
                    file_item.get(
                        "filename"
                    )
                )

                content_type_item = (
                    file_item.get(
                        "content_type"
                    )
                    or "image/jpeg"
                )

                if (
                    not file_bytes_item
                    or not filename_item
                ):
                    continue

                storage_info = (
                    self.storage_service
                    .upload_image(
                        file_bytes=file_bytes_item,
                        filename=filename_item,
                        content_type=content_type_item,
                    )
                )

                phash_val, ahash_val = (
                    self._calculate_image_hashes(
                        file_bytes_item
                    )
                )

                files_data.append(
                    {
                        "image_hd_url": (
                            storage_info[
                                "hd_url"
                            ]
                        ),
                        "thumbnail_url": (
                            storage_info[
                                "thumbnail_url"
                            ]
                        ),
                        "file_hash": (
                            storage_info[
                                "sha256"
                            ]
                        ),
                        "width_px": (
                            storage_info[
                                "width"
                            ]
                        ),
                        "height_px": (
                            storage_info[
                                "height"
                            ]
                        ),
                        "file_size_bytes": (
                            storage_info[
                                "file_size"
                            ]
                        ),
                        "phash": phash_val,
                        "ahash": ahash_val,
                    }
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
                files_data=(
                    files_data
                    if files_data
                    else None
                ),
                film_metadata=(
                    film_metadata
                ),
            )
        )

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

        self._validate_round_status_for_submission(submission.round_id)

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

        # -----------------------------------------------------
        # Update status
        # -----------------------------------------------------

        from datetime import datetime, timezone

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
        # AI detection
        # -----------------------------------------------------

        if (
            submission_file
            and submission_file.image_hd_url
        ):

            try:

                from services.ai_detection_service import (
                    AiDetectionService,
                )

                ai_service = (
                    AiDetectionService()
                )

                ai_result = (
                    ai_service.detect_ai(
                        submission_file.image_hd_url
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

                risk_level = ai_result.get(
                    "risk_level",
                    "safe",
                )

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
                    },
                )

            except Exception:
                pass

            # -------------------------------------------------
            # Duplicate detection
            # -------------------------------------------------

            try:

                local_path = (
                    submission_file.image_hd_url
                )

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
                                submission_file.image_hd_url,
                                temp_file.name,
                            )

                            local_path = (
                                temp_file.name
                            )

                        except Exception:
                            pass

                if os.path.exists(local_path):

                    with open(
                        local_path,
                        "rb",
                    ) as f:
                        file_bytes = f.read()

                    # Ensure hashes exist
                    phash_val, ahash_val = (
                        self._calculate_image_hashes(
                            file_bytes
                        )
                    )

                    if (
                        phash_val is not None
                        or ahash_val is not None
                    ):
                        submission_file.phash = (
                            phash_val
                        )
                        submission_file.ahash = (
                            ahash_val
                        )

                        self.submission_repo.session.commit()

                    self._run_duplicate_check_and_flag(
                        updated_submission,
                        file_bytes,
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
    ) -> Optional[
        Tuple[
            SubmissionModel,
            Optional[SubmissionFileModel],
            Optional[SubmissionFilmMetadataModel],
        ]
    ]:

        return (
            self.submission_repo
            .get_by_id_with_details(
                submission_id
            )
        )

    # =========================================================
    # GET SUBMISSION DETAIL
    # =========================================================

    def get_submission_detail(
        self,
        submission_id: int,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
    ) -> Optional[
        Dict[str, Any]
    ]:

        result = (
            self.submission_repo
            .get_by_id_with_details(
                submission_id
            )
        )

        if not result:
            return None
            
        submission, submission_file, film_metadata = result
        ai_flags = self.submission_repo.get_all_ai_flags(submission_id)

        data = self._format_submission_dict(
            submission,
            submission_file,
            film_metadata,
            ai_flags
        )

        if (
            role == "participant"
            and user_id is not None
        ):

            if (
                data["user_id"]
                != user_id
            ):
                raise PermissionError(
                    "Access forbidden: You can only view your own submission details."
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
    ) -> SubmissionModel:

        if (
            file_bytes
            and len(file_bytes) > 0
            and filename
        ):

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
                storage_info["hd_url"]
            )

            thumbnail_url = (
                storage_info[
                    "thumbnail_url"
                ]
            )

            file_hash = (
                storage_info["sha256"]
            )

            width_px = (
                storage_info["width"]
            )

            height_px = (
                storage_info["height"]
            )

            file_size_bytes = (
                storage_info["file_size"]
            )
        # -----------------------------------------------------
        # Validate Round status before submitting a draft
        # -----------------------------------------------------
        #
        # A participant may edit a draft regardless of the
        # Round status, but the draft must only be converted
        # to "submitted" while the Round is "ongoing".
        #
        # This prevents bypassing the submission restriction
        # through the update-draft endpoint.
        # -----------------------------------------------------

        if status == "submitted":

            target_round_id = round_id

            # If round_id is not provided, use the submission's
            # existing round.
            if target_round_id is None:
                existing_submission = (
                    self.submission_repo
                    .get_by_id(submission_id)
                )

                if not existing_submission:
                    raise ValueError(
                        "Submission not found"
                    )

                target_round_id = (
                    existing_submission.round_id
                )

            self._validate_round_status_for_submission(
                target_round_id
            )

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
        # AI detection if submitted
        # -----------------------------------------------------

        if (
            status == "submitted"
            and image_hd_url
        ):

            try:

                from services.ai_detection_service import (
                    AiDetectionService,
                )

                ai_service = (
                    AiDetectionService()
                )

                ai_result = (
                    ai_service.detect_ai(
                        image_hd_url
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

                risk_level = ai_result.get(
                    "risk_level",
                    "safe",
                )

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
                    },
                )

            except Exception:
                pass

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
        Run perceptual duplicate detection.

        This method must never block submission creation.
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

            is_dup = bool(
                dup_result.get(
                    "is_duplicate",
                    False,
                )
            )

            if is_dup:

                risk_level = "high"
                status = "pending"

            elif similarity >= 70.0:

                risk_level = "medium"
                status = "pending"

            else:

                risk_level = "safe"
                status = "clear"

            saved_flag = (
                self.submission_repo
                .save_ai_flag(
                    submission_id=(
                        submission.id
                    ),
                    confidence_score=(
                        similarity
                    ),
                    risk_level=(
                        risk_level
                    ),
                    flag_type=(
                        "duplicate_similarity"
                    ),
                    status=status,
                )
            )

            matched_sub_id = (
                dup_result.get(
                    "matched_submission_id"
                )
            )

            # IMPORTANT:
            # Repository now supports
            # similarity_matched_submission_id.
            self.submission_repo.save_ai_analysis_report(
                submission_id=(
                    submission.id
                ),
                ai_flag_id=(
                    saved_flag.id
                ),
                ai_model_name=(
                    "Duplicate Detection Engine"
                ),
                ai_confidence_score=(
                    similarity
                ),
                raw_details=dup_result,
                similarity_matched_submission_id=(
                    matched_sub_id
                ),
            )

        except Exception as e:

            # Duplicate detection is optional.
            # It must never break submission creation.
            print(
                f"Warning: duplicate check failed: {e}"
            )

    # =========================================================
    # FORMAT SUBMISSION
    # =========================================================

    def _format_submission_dict(
        self,
        submission: SubmissionModel,
        submission_file: Optional[
            SubmissionFileModel
        ] = None,
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
            "film_metadata": None,
            "ai_flags": [],
        }

        if submission_file:

            item["file"] = {
                "id": submission_file.id,
                "image_hd_url": (
                    submission_file.image_hd_url
                ),
                "thumbnail_url": (
                    submission_file.thumbnail_url
                ),
                "width_px": (
                    submission_file.width_px
                ),
                "height_px": (
                    submission_file.height_px
                ),
                "file_size_bytes": (
                    submission_file.file_size_bytes
                ),
                "file_hash": (
                    submission_file.file_hash
                ),
                "phash": (
                    submission_file.phash
                ),
                "ahash": (
                    submission_file.ahash
                ),
                "created_at": (
                    submission_file.created_at.isoformat()
                    if submission_file.created_at
                    else None
                ),
            }

        if film_metadata:

            item["film_metadata"] = {
                "film_stock": (
                    film_metadata.film_stock
                ),
                "film_iso": (
                    film_metadata.film_iso
                ),
                "camera_body": (
                    film_metadata.camera_body
                ),
                "lens": (
                    film_metadata.lens
                ),
                "lab_name": (
                    film_metadata.lab_name
                ),
                "scanner_info": (
                    film_metadata.scanner_info
                ),
                "development_process": (
                    film_metadata.development_process
                ),
                "taken_at_location": (
                    film_metadata.taken_at_location
                ),
                "created_at": (
                    film_metadata.created_at.isoformat()
                    if film_metadata.created_at
                    else None
                ),
            }

        if ai_flags:
            item["ai_flags"] = [
                {
                    "id": flag.id,
                    "flag_type": flag.flag_type,
                    "ai_score": (
                        float(flag.confidence_score)
                        if flag.confidence_score is not None
                        else None
                    ),
                    "risk_level": flag.risk_level,
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

        submissions = [
            self._format_submission_dict(
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            )
            for (
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            ) in rows
        ]

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

        submissions = [
            self._format_submission_dict(
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            )
            for (
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            ) in rows
        ]

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

        submissions = [
            self._format_submission_dict(
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            )
            for (
                sub,
                file_obj,
                meta_obj,
                ai_obj,
            ) in rows
        ]

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

        submissions = [
            self._format_submission_dict(
                sub,
                file_obj,
                meta_obj,
                ai_objs,
            )
            for (
                sub,
                file_obj,
                meta_obj,
                ai_objs,
            ) in rows
        ]

        return {
            "submissions": submissions,
            "total": len(submissions),
        }
        
    def update_flag_status(
        self,
        flag_id: int,
        status: str,
    ) -> Optional[Dict[str, Any]]:
        
        flag = self.submission_repo.update_ai_flag_status(flag_id, status)
        if not flag:
            return None
            
        return {
            "id": flag.id,
            "flag_type": flag.flag_type,
            "ai_score": (
                float(flag.confidence_score)
                if flag.confidence_score is not None
                else None
            ),
            "risk_level": flag.risk_level,
            "status": flag.status,
        }