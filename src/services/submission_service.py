import math
import threading
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from infrastructure.repositories.submission_repository import (
    SubmissionRepository,
)

from services.storage_service import StorageService

from infrastructure.models.app import (
    SubmissionModel,
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
    - negative
    - negative_film
    - contact_sheet

    Responsibilities:
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
    - Public Gallery
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
    # ROUND VALIDATION
    # =========================================================

    def _validate_round_status_for_submission(
        self,
        round_id: Optional[int],
    ):
        """
        A submission can only be submitted while
        the round is ongoing.
        """

        if not round_id:
            return

        session = getattr(
            self.submission_repo,
            "session",
            None,
        )

        if not session:
            return

        try:
            from infrastructure.models.app import RoundModel

            round_obj = (
                session.query(RoundModel)
                .filter_by(id=round_id)
                .first()
            )

            if not round_obj:
                return

            status_str = (
                round_obj.status or ""
            ).lower()

            if status_str != "ongoing":
                raise ValueError(
                    f"Cannot submit to round with "
                    f"status '{round_obj.status}'"
                )

        except ValueError:
            raise

        except Exception:
            # Do not break application if RoundModel
            # is unavailable.
            pass

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

        normalized = (
            str(file_type)
            .strip()
            .lower()
        )

        if normalized not in self.ALLOWED_FILE_TYPES:
            raise ValueError(
                "Invalid file_type. Allowed values: "
                "main_image, negative, "
                "negative_film, contact_sheet"
            )

        return normalized

    def _validate_file_type(
        self,
        file_type: Optional[str],
    ) -> str:
        return self._normalize_file_type(
            file_type
        )

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

        file_type = (
            self._normalize_file_type(
                file_item.get("file_type")
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

        return (
            self.storage_service.upload_image(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
        )

    # =========================================================
    # UPLOAD FILE
    # =========================================================

    def _upload_file_item(
        self,
        file_item: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Upload one file and convert it to
        repository format.
        """

        normalized = (
            self._normalize_file_item(
                file_item
            )
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

        phash_val, ahash_val = (
            self._calculate_image_hashes(
                file_bytes
            )
        )

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
                not normalized["file_bytes"]
                or not normalized["filename"]
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

        # -----------------------------------------------------
        # Validate round
        # -----------------------------------------------------

        if status != "draft":
            self._validate_round_status_for_submission(
                round_id
            )

        files_data = []

        # -----------------------------------------------------
        # Multiple files
        # -----------------------------------------------------

        if files:
            files_data = (
                self._build_files_data(
                    files
                )
            )

        # -----------------------------------------------------
        # Single file upload
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Existing file information
        # -----------------------------------------------------

        elif image_hd_url:

            normalized_file_type = (
                self._normalize_file_type(
                    file_type
                )
            )

            files_data.append(
                {
                    "file_type": normalized_file_type,
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

        # -----------------------------------------------------
        # Validate submitted submission
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Find main image
        # -----------------------------------------------------

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

        if (
            main_image is None
            and files_data
        ):
            main_image = files_data[0]

        first_file = (
            main_image or {}
        )

        # -----------------------------------------------------
        # Create submission
        # -----------------------------------------------------

        submission = (
            self.submission_repo
            .create_submission(
                round_id=round_id,
                user_id=user_id,
                title=title,
                image_hd_url=first_file.get(
                    "image_hd_url"
                ),
                file_hash=first_file.get(
                    "file_hash"
                ),
                thumbnail_url=first_file.get(
                    "thumbnail_url"
                ),
                width_px=first_file.get(
                    "width_px"
                ),
                height_px=first_file.get(
                    "height_px"
                ),
                file_size_bytes=first_file.get(
                    "file_size_bytes"
                ),
                files_data=files_data,
                story_description=story_description,
                film_stock=film_metadata.get(
                    "film_stock"
                ) or "",
                film_iso=film_metadata.get(
                    "film_iso"
                ),
                camera_body=film_metadata.get(
                    "camera_body"
                ),
                lens=film_metadata.get(
                    "lens"
                ),
                lab_name=film_metadata.get(
                    "lab_name"
                ),
                scanner_info=film_metadata.get(
                    "scanner_info"
                ),
                development_process=(
                    film_metadata.get(
                        "development_process"
                    )
                    or "C-41"
                ),
                taken_at_location=film_metadata.get(
                    "taken_at_location"
                ),
                status=status,
            )
        )

        # -----------------------------------------------------
        # Background AI + Duplicate processing
        # -----------------------------------------------------

        if status != "draft":

            self._initialize_pending_ai_flags(
                submission.id
            )

            first_bytes = None

            if files:

                for file_item in files:

                    item_type = (
                        self._normalize_file_type(
                            file_item.get(
                                "file_type"
                            )
                        )
                    )

                    if item_type == "main_image":

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

            self._start_ai_pipeline(
                submission_id=submission.id,
                image_url=first_file.get(
                    "image_hd_url"
                ),
                file_bytes=first_bytes,
                film_metadata=film_metadata,
            )

        return submission

    # =========================================================
    # INITIAL AI FLAGS
    # =========================================================

    def _initialize_pending_ai_flags(
        self,
        submission_id: int,
    ):
        """
        Create pending AI flags before background processing.
        """

        try:

            self.submission_repo.save_ai_flag(
                submission_id=submission_id,
                confidence_score=0.0,
                risk_level="safe",
                flag_type="AI_METADATA",
                status="pending",
            )

            self.submission_repo.save_ai_flag(
                submission_id=submission_id,
                confidence_score=0.0,
                risk_level="safe",
                flag_type="duplicate_similarity",
                status="pending",
            )

        except Exception as e:

            print(
                "Warning: could not create "
                f"initial pending flags: {e}"
            )

    # =========================================================
    # BACKGROUND AI PIPELINE
    # =========================================================

    def _start_ai_pipeline(
        self,
        submission_id: int,
        image_url: Optional[str],
        file_bytes: Optional[bytes],
        film_metadata: Dict[str, Any],
    ):
        """
        Run AI detection and duplicate detection
        in background.
        """

        def ai_pipeline_thread(
            sub_id,
            hd_url,
            f_bytes,
            metadata,
        ):

            repo = None

            try:
                repo = SubmissionRepository()

            except Exception as e:

                print(
                    f"Background repository init failed: {e}"
                )

                return

            # -------------------------------------------------
            # Fetch contest settings
            # -------------------------------------------------

            duplicate_threshold = 70.0
            ai_risk_threshold = 70.0

            try:

                from infrastructure.models.app import (
                    ContestSettingsModel,
                )

                sub_for_settings = (
                    repo.session
                    .query(SubmissionModel)
                    .filter_by(id=sub_id)
                    .first()
                )

                if (
                    sub_for_settings
                    and sub_for_settings.round
                    and sub_for_settings.round.contest
                ):

                    contest_id = (
                        sub_for_settings
                        .round
                        .contest
                        .id
                    )

                    c_settings = (
                        repo.session
                        .query(
                            ContestSettingsModel
                        )
                        .filter_by(
                            contest_id=contest_id
                        )
                        .first()
                    )

                    if c_settings:

                        if getattr(
                            c_settings,
                            "ai_duplicate_threshold",
                            None,
                        ) is not None:

                            duplicate_threshold = float(
                                c_settings.ai_duplicate_threshold
                            )

                        if getattr(
                            c_settings,
                            "ai_risk_threshold",
                            None,
                        ) is not None:

                            ai_risk_threshold = float(
                                c_settings.ai_risk_threshold
                            )

            except Exception as e:

                print(
                    "Failed to fetch contest settings "
                    f"for AI thresholds: {e}"
                )

            # -------------------------------------------------
            # Fraud notification
            # -------------------------------------------------

            def notify_fraud(
                risk,
                fraud_type,
            ):

                if risk not in [
                    "medium",
                    "high",
                ]:
                    return

                try:

                    from infrastructure.models.app import (
                        UserModel,
                        RoleModel,
                        user_roles,
                    )

                    from services.notification_service import (
                        NotificationService,
                    )

                    from infrastructure.repositories.notification_repository import (
                        NotificationRepository,
                    )

                    notif_repo = (
                        NotificationRepository(
                            session=repo.session
                        )
                    )

                    notif_service = (
                        NotificationService(
                            repository=notif_repo
                        )
                    )

                    sub = (
                        repo.session
                        .query(SubmissionModel)
                        .filter_by(id=sub_id)
                        .first()
                    )

                    if (
                        not sub
                        or not sub.round
                        or not sub.round.contest
                    ):
                        return

                    contest = sub.round.contest

                    title = (
                        "Cảnh báo gian lận mức độ "
                        f"{risk.upper()}"
                    )

                    body = (
                        f"Phát hiện rủi ro {fraud_type} "
                        f"ở bài dự thi #{sub_id}."
                    )

                    notif_service.create_notification(
                        user_id=contest.created_by,
                        title=title,
                        body=body,
                        contest_id=contest.id,
                        notification_type="fraud_alert",
                    )

                    admins = (
                        repo.session
                        .query(UserModel)
                        .join(user_roles)
                        .join(RoleModel)
                        .filter(
                            RoleModel.code == "admin"
                        )
                        .all()
                    )

                    for admin in admins:

                        if admin.id == contest.created_by:
                            continue

                        notif_service.create_notification(
                            user_id=admin.id,
                            title=title,
                            body=body,
                            contest_id=contest.id,
                            notification_type="fraud_alert",
                        )

                except Exception as e:

                    print(
                        "Failed to send fraud notification: "
                        f"{e}"
                    )

            # -------------------------------------------------
            # AI Detection
            # -------------------------------------------------

            if hd_url:

                try:

                    from services.ai_detection_service import (
                        AiDetectionService,
                    )

                    ai_service = (
                        AiDetectionService()
                    )

                    ai_result = (
                        ai_service.detect_ai(
                            hd_url
                        )
                    )

                    if not isinstance(
                        ai_result,
                        dict,
                    ):
                        ai_result = {}

                    comparison_result = (
                        ai_service
                        .compare_metadata_with_exif(
                            metadata,
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

                    base_risk = (
                        ai_result.get(
                            "risk_level",
                            "safe",
                        )
                        or "safe"
                    )

                    comp_risk = (
                        comparison_result.get(
                            "risk_level",
                            "safe",
                        )
                        or "safe"
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

                    # Apply configured AI threshold
                    if (
                        ai_score >= ai_risk_threshold
                        and risk_level == "safe"
                    ):
                        risk_level = "medium"

                    saved_flag = (
                        repo.save_ai_flag(
                            submission_id=sub_id,
                            confidence_score=ai_score,
                            risk_level=risk_level,
                            flag_type="AI_METADATA",
                            status="completed",
                        )
                    )

                    repo.save_ai_analysis_report(
                        submission_id=sub_id,
                        ai_flag_id=saved_flag.id,
                        ai_model_name=(
                            "EXIF Extraction Engine"
                        ),
                        ai_confidence_score=ai_score,
                        raw_details={
                            "exif_data": ai_result.get(
                                "exif_data",
                                {},
                            ),
                            "raw_exif": ai_result.get(
                                "raw_exif",
                                {},
                            ),
                            "metadata_comparison": (
                                comparison_result
                            ),
                            "applied_thresholds": {
                                "ai_risk": ai_risk_threshold,
                            },
                        },
                    )

                    notify_fraud(
                        risk_level,
                        "AI_METADATA",
                    )

                except Exception as e:

                    print(
                        "Background AI task failed: "
                        f"{e}"
                    )

                    try:

                        flag = (
                            repo.get_ai_flag(
                                sub_id,
                                "AI_METADATA",
                            )
                        )

                        if flag:

                            repo.update_ai_flag_status(
                                flag.id,
                                "failed",
                            )

                    except Exception as flag_error:

                        print(
                            "Failed to update AI flag status: "
                            f"{flag_error}"
                        )

            # -------------------------------------------------
            # Duplicate Detection
            # -------------------------------------------------

            if f_bytes:

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
                            new_image_bytes=f_bytes,
                            exclude_submission_id=sub_id,
                            session=repo.session,
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

                    elif (
                        similarity
                        >= duplicate_threshold
                    ):

                        risk_level = "medium"

                    else:

                        risk_level = "safe"

                    flag_status = (
                        "pending"
                        if risk_level in [
                            "medium",
                            "high",
                        ]
                        else "clear"
                    )

                    saved_flag = (
                        repo.save_ai_flag(
                            submission_id=sub_id,
                            confidence_score=similarity,
                            risk_level=risk_level,
                            flag_type="duplicate_similarity",
                            status=flag_status,
                        )
                    )

                    matched_sub_id = (
                        dup_result.get(
                            "matched_submission_id"
                        )
                    )

                    raw_details = {
                        **dup_result,
                        "applied_thresholds": {
                            "duplicate": (
                                duplicate_threshold
                            ),
                        },
                    }

                    # Try extended repository signature
                    try:

                        repo.save_ai_analysis_report(
                            submission_id=sub_id,
                            ai_flag_id=saved_flag.id,
                            ai_model_name=(
                                "Duplicate Detection Engine"
                            ),
                            ai_confidence_score=similarity,
                            raw_details=raw_details,
                            similarity_matched_submission_id=(
                                matched_sub_id
                            ),
                        )

                    except TypeError:

                        repo.save_ai_analysis_report(
                            submission_id=sub_id,
                            ai_flag_id=saved_flag.id,
                            ai_model_name=(
                                "Duplicate Detection Engine"
                            ),
                            ai_confidence_score=similarity,
                            raw_details=raw_details,
                        )

                    notify_fraud(
                        risk_level,
                        "duplicate_similarity",
                    )

                except Exception as e:

                    print(
                        "Background Duplicate task failed: "
                        f"{e}"
                    )

                    try:

                        flag = (
                            repo.get_ai_flag(
                                sub_id,
                                "duplicate_similarity",
                            )
                        )

                        if flag:

                            repo.update_ai_flag_status(
                                flag.id,
                                "failed",
                            )

                    except Exception:
                        pass

        # -----------------------------------------------------
        # Fire and forget
        # -----------------------------------------------------

        thread = threading.Thread(
            target=ai_pipeline_thread,
            args=(
                submission_id,
                image_url,
                file_bytes,
                film_metadata,
            ),
            daemon=True,
        )

        thread.start()

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
                "Cannot edit submission that "
                "is not in draft status"
            )

        files_data = []

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
                film_metadata=film_metadata,
            )
        )

    def update_draft_submission(
        self,
        *args,
        **kwargs,
    ):
        return self.update_draft(
            *args,
            **kwargs,
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

        submission = (
            result[0]
        )

        submission_file = (
            result[1]
            if len(result) > 1
            else None
        )

        film_metadata = (
            result[2]
            if len(result) > 2
            else None
        )

        # -----------------------------------------------------
        # Ownership
        # -----------------------------------------------------

        if submission.user_id != user_id:
            raise PermissionError(
                "Forbidden"
            )

        # -----------------------------------------------------
        # Status
        # -----------------------------------------------------

        if submission.status != "draft":
            raise ValueError(
                "Cannot submit submission that "
                "is not in draft status"
            )

        # -----------------------------------------------------
        # Round
        # -----------------------------------------------------

        round_id = getattr(
            submission,
            "round_id",
            None,
        )

        if round_id is not None:
            self._validate_round_status_for_submission(
                round_id
            )

        # -----------------------------------------------------
        # Title
        # -----------------------------------------------------

        if (
            not submission.title
            or not submission.title.strip()
        ):
            raise ValueError(
                "title is required"
            )

        # -----------------------------------------------------
        # File
        # -----------------------------------------------------

        if not submission_file:
            raise ValueError(
                "At least one image file is required"
            )

        # -----------------------------------------------------
        # Film metadata
        # -----------------------------------------------------

        if (
            not film_metadata
            or not getattr(
                film_metadata,
                "film_stock",
                None,
            )
            or not film_metadata.film_stock.strip()
        ):
            raise ValueError(
                "film_stock is required"
            )

        # -----------------------------------------------------
        # Update status
        # -----------------------------------------------------

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
        # Get image URL
        # -----------------------------------------------------

        image_url = getattr(
            submission_file,
            "image_hd_url",
            None,
        )

        # -----------------------------------------------------
        # AI detection
        # -----------------------------------------------------

        if image_url:

            try:

                self._run_ai_detection(
                    submission=submission,
                    image_url=image_url,
                    film_metadata={
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
                    },
                )

            except Exception as e:

                print(
                    f"Warning: AI detection failed: {e}"
                )

        return updated_submission

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

            base_risk = (
                ai_result.get(
                    "risk_level",
                    "safe",
                )
                or "safe"
            )

            comp_risk = (
                comparison_result.get(
                    "risk_level",
                    "safe",
                )
                or "safe"
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
                    status="completed",
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
                    "exif_data": ai_result.get(
                        "exif_data",
                        {},
                    ),
                    "raw_exif": ai_result.get(
                        "raw_exif",
                        {},
                    ),
                    "metadata_comparison": (
                        comparison_result
                    ),
                },
            )

        except Exception as e:

            print(
                f"Error in _run_ai_detection: {e}"
            )

            try:

                flag = (
                    self.submission_repo
                    .get_ai_flag(
                        submission.id,
                        "AI_METADATA",
                    )
                )

                if flag:

                    self.submission_repo.update_ai_flag_status(
                        flag.id,
                        "failed",
                    )

            except Exception as flag_error:

                print(
                    "Failed to update AI flag status: "
                    f"{flag_error}"
                )

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

    # =========================================================
    # LIST SUBMISSIONS
    # =========================================================

    def list_submissions(self):

        return (
            self.submission_repo
            .list()
        )

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
        # Get files
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
        # Fallback repository file
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
        # Film metadata
        # -----------------------------------------------------

        film_metadata = (
            result[2]
            if len(result) > 2
            else None
        )

        # -----------------------------------------------------
        # AI flags
        # -----------------------------------------------------

        ai_flags = (
            self.submission_repo
            .get_all_ai_flags(
                submission_id
            )
        )

        # -----------------------------------------------------
        # Format
        # -----------------------------------------------------

        data = (
            self._format_submission_dict(
                submission,
                submission_files,
                film_metadata,
                ai_flags,
            )
        )

        if not isinstance(
            data,
            dict,
        ):
            data = {}

        # -----------------------------------------------------
        # Participant permission
        # -----------------------------------------------------

        if (
            role == "participant"
            and user_id is not None
        ):

            if data.get(
                "user_id"
            ) != user_id:

                raise PermissionError(
                    "Access forbidden: "
                    "You can only view your own "
                    "submission details."
                )

        return data

    # =========================================================
    # UPDATE DRAFT SUBMISSION FULL
    # =========================================================

    def update_draft_submission_full(
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

        normalized_file_type = (
            self._normalize_file_type(
                file_type
            )
        )

        # -----------------------------------------------------
        # Upload new file
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Validate round when submitting
        # -----------------------------------------------------

        if status == "submitted":

            target_round_id = round_id

            if target_round_id is None:

                existing_submission = (
                    self.submission_repo
                    .get_by_id(
                        submission_id
                    )
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
                    film_metadata=film_metadata,
                    image_hd_url=image_hd_url,
                    thumbnail_url=thumbnail_url,
                    file_hash=file_hash,
                    width_px=width_px,
                    height_px=height_px,
                    file_size_bytes=file_size_bytes,
                    file_type=normalized_file_type,
                )
            )

        except TypeError:

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
                    film_metadata=film_metadata,
                    image_hd_url=image_hd_url,
                    thumbnail_url=thumbnail_url,
                    file_hash=file_hash,
                    width_px=width_px,
                    height_px=height_px,
                    file_size_bytes=file_size_bytes,
                )
            )

        # -----------------------------------------------------
        # AI detection
        # -----------------------------------------------------

        if (
            status == "submitted"
            and image_hd_url
        ):

            try:

                self._run_ai_detection(
                    submission=submission,
                    image_url=image_hd_url,
                    film_metadata=(
                        film_metadata
                        or {}
                    ),
                )

            except Exception as e:

                print(
                    f"Warning: AI detection failed: {e}"
                )

        return submission

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
                    exclude_submission_id=submission.id,
                    session=self.submission_repo.session,
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
                    flag_type="duplicate_similarity",
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
    # FORMAT FILE
    # =========================================================

    def _format_file_dict(
        self,
        submission_file: Any,
    ) -> Dict[str, Any]:

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
                "image_hd_url": submission_file.get(
                    "image_hd_url"
                ),
                "thumbnail_url": submission_file.get(
                    "thumbnail_url"
                ),
                "width_px": submission_file.get(
                    "width_px"
                ),
                "height_px": submission_file.get(
                    "height_px"
                ),
                "file_size_bytes": submission_file.get(
                    "file_size_bytes"
                ),
                "file_hash": submission_file.get(
                    "file_hash"
                ),
                "phash": submission_file.get(
                    "phash"
                ),
                "ahash": submission_file.get(
                    "ahash"
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
            "files": {
                "main_image": [],
                "negative": [],
                "negative_film": [],
                "contact_sheet": [],
            },
            "proof_files": [],
            "film_metadata": (
                self._format_film_metadata(
                    film_metadata
                )
            ),
            "ai_flags": [],
        }

        # -----------------------------------------------------
        # Collect all files
        # -----------------------------------------------------

        all_submission_files = []

        if (
            hasattr(
                submission,
                "files",
            )
            and submission.files is not None
        ):

            try:

                if len(submission.files) > 0:

                    all_submission_files = list(
                        submission.files
                    )

            except TypeError:

                all_submission_files = [
                    submission.files
                ]

        if (
            not all_submission_files
            and submission_file
        ):

            if isinstance(
                submission_file,
                (list, tuple, set),
            ):

                all_submission_files = list(
                    submission_file
                )

            else:

                all_submission_files = [
                    submission_file
                ]

        # -----------------------------------------------------
        # Format files
        # -----------------------------------------------------

        formatted_files = []

        for file_obj in all_submission_files:

            if not file_obj:
                continue

            file_dict = (
                self._format_file_dict(
                    file_obj
                )
            )

            formatted_files.append(
                file_dict
            )

        # -----------------------------------------------------
        # Categorize
        # -----------------------------------------------------

        for file_dict in formatted_files:

            file_type = (
                file_dict.get(
                    "file_type"
                )
                or self.DEFAULT_FILE_TYPE
            )

            if file_type not in item["files"]:
                item["files"][file_type] = []

            item["files"][file_type].append(
                file_dict
            )

        # -----------------------------------------------------
        # Main image
        # -----------------------------------------------------

        main_file = None

        for file_dict in formatted_files:

            if (
                file_dict.get(
                    "file_type"
                )
                == "main_image"
            ):

                main_file = file_dict
                break

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
            file_dict
            for file_dict in formatted_files
            if file_dict.get(
                "file_type"
            ) != "main_image"
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

        submissions: List[Dict[str, Any]] = []

        for row in rows or []:

            sub = None
            file_obj = None
            meta_obj = None
            ai_obj = None

            if isinstance(
                row,
                tuple,
            ):

                sub = (
                    row[0]
                    if len(row) > 0
                    else None
                )

                file_obj = (
                    row[1]
                    if len(row) > 1
                    else None
                )

                meta_obj = (
                    row[2]
                    if len(row) > 2
                    else None
                )

                ai_obj = (
                    row[3]
                    if len(row) > 3
                    else None
                )

            else:

                sub = row

            if sub is None:
                continue

            submissions.append(
                self._format_submission_dict(
                    sub,
                    file_obj,
                    meta_obj,
                    ai_obj,
                )
            )

        return {
            "message": (
                "My submissions retrieved successfully"
            ),
            "submissions": submissions,
            "count": len(submissions),
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

        for row in rows or []:

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

        for row in rows or []:

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

    # =========================================================
    # GET AI ANALYSIS REPORT
    # =========================================================

    def get_submission_ai_report(
        self,
        submission_id: int,
    ) -> dict:

        flags = (
            self.submission_repo
            .get_all_ai_flags(
                submission_id
            )
        )

        from infrastructure.models.app.app_audit_log_model import (
            AuditLogModel,
        )

        from infrastructure.models.app.app_submission_model import (
            SubmissionModel,
        )

        result = []

        for flag in flags or []:

            flag_dict = {
                "id": flag.id,
                "flag_type": flag.flag_type,
                "confidence_score": (
                    float(
                        flag.confidence_score
                    )
                    if flag.confidence_score
                    is not None
                    else None
                ),
                "risk_level": flag.risk_level,
                "status": flag.status,
                "reviewed_by": flag.reviewed_by,
                "reviewed_at": (
                    flag.reviewed_at.isoformat()
                    if flag.reviewed_at
                    else None
                ),
                "review_notes": (
                    flag.review_notes
                ),
                "created_at": (
                    flag.created_at.isoformat()
                    if flag.created_at
                    else None
                ),
                "updated_at": (
                    flag.updated_at.isoformat()
                    if flag.updated_at
                    else None
                ),
                "raw_details": None,
                "similarity_matched_submission": None,
                "history": [],
            }

            # -------------------------------------------------
            # Analysis report
            # -------------------------------------------------

            if flag.analysis_report:

                flag_dict["raw_details"] = (
                    flag.analysis_report.raw_details
                )

                matched_id = (
                    flag.analysis_report
                    .similarity_matched_submission_id
                )

                if matched_id:

                    matched_sub = (
                        self.submission_repo
                        .session
                        .query(SubmissionModel)
                        .filter(
                            SubmissionModel.id
                            == matched_id
                        )
                        .first()
                    )

                    if matched_sub:

                        flag_dict[
                            "similarity_matched_submission"
                        ] = {
                            "id": matched_sub.id,
                            "title": matched_sub.title,
                            "author_id": (
                                matched_sub.user_id
                            ),
                        }

            # -------------------------------------------------
            # Audit history
            # -------------------------------------------------

            audit_logs = (
                self.submission_repo
                .session
                .query(AuditLogModel)
                .filter(
                    AuditLogModel.entity_name
                    == "ai_flags",
                    AuditLogModel.entity_id
                    == flag.id,
                )
                .order_by(
                    AuditLogModel.created_at.asc()
                )
                .all()
            )

            for log in audit_logs:

                flag_dict[
                    "history"
                ].append(
                    {
                        "id": log.id,
                        "action": log.action,
                        "old_value": log.old_value,
                        "new_value": log.new_value,
                        "created_at": (
                            log.created_at.isoformat()
                            if log.created_at
                            else None
                        ),
                        "user_id": log.user_id,
                    }
                )

            result.append(
                flag_dict
            )

        return {
            "submission_id": submission_id,
            "ai_flags": result,
        }

    # =========================================================
    # PUBLIC GALLERY
    # =========================================================

    def get_public_gallery(
        self,
        film_stock: Optional[str] = None,
        camera_model: Optional[str] = None,
        contest_id: Optional[int] = None,
        year: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get public gallery submissions with
        filtering and pagination.
        """

        # -----------------------------------------------------
        # Normalize pagination
        # -----------------------------------------------------

        try:
            page = int(page)
        except (TypeError, ValueError):
            page = 1

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 20

        if page < 1:
            page = 1

        if limit < 1:
            limit = 20

        # -----------------------------------------------------
        # Repository
        # -----------------------------------------------------

        items, total = (
            self.submission_repo
            .get_public_gallery(
                film_stock=film_stock,
                camera_model=camera_model,
                contest_id=contest_id,
                year=year,
                page=page,
                limit=limit,
            )
        )

        total_pages = (
            math.ceil(
                total / limit
            )
            if limit > 0
            else 0
        )

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "items": items,
        }