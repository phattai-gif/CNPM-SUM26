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

        film_metadata = film_metadata or {}

        files_data = []

        # =====================================================
        # UPLOAD MULTIPLE FILES
        # =====================================================

        if files:

            for file_item in files:

                file_bytes_item = file_item.get(
                    "file_bytes"
                )

                filename_item = file_item.get(
                    "filename"
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

                files_data.append(
                    {
                        "image_hd_url": (
                            storage_info["hd_url"]
                        ),
                        "thumbnail_url": (
                            storage_info[
                                "thumbnail_url"
                            ]
                        ),
                        "file_hash": (
                            storage_info["sha256"]
                        ),
                        "width_px": (
                            storage_info["width"]
                        ),
                        "height_px": (
                            storage_info["height"]
                        ),
                        "file_size_bytes": (
                            storage_info["file_size"]
                        ),
                    }
                )

        # =====================================================
        # BACKWARD-COMPATIBLE SINGLE FILE UPLOAD
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

            files_data.append(
                {
                    "image_hd_url": (
                        storage_info["hd_url"]
                    ),
                    "thumbnail_url": (
                        storage_info[
                            "thumbnail_url"
                        ]
                    ),
                    "file_hash": (
                        storage_info["sha256"]
                    ),
                    "width_px": (
                        storage_info["width"]
                    ),
                    "height_px": (
                        storage_info["height"]
                    ),
                    "file_size_bytes": (
                        storage_info["file_size"]
                    ),
                }
            )

        # =====================================================
        # BACKWARD-COMPATIBLE EXISTING FILE URL
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

            if not film_metadata.get("film_stock"):
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

        first_thumbnail_url = first_file.get(
            "thumbnail_url"
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
                        "development_process",
                        "C-41",
                    )
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
        #
        # AI is OPTIONAL.
        # AI failure MUST NOT block submission creation.
        # =====================================================

        if first_hd_url:

            try:

                try:
                    from services.ai_detection_service import (
                        AiDetectionService,
                    )
                except ImportError:
                    from services.ai_detection_service import (
                        AiDetectionService,
                    )

                ai_service = (
                    AiDetectionService()
                )

                # -------------------------------------------------
                # AI detection
                # -------------------------------------------------

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

                # -------------------------------------------------
                # Base AI score
                # -------------------------------------------------

                ai_score = ai_result.get(
                    "ai_score",
                    0,
                )

                # -------------------------------------------------
                # Compare film metadata with EXIF
                # -------------------------------------------------

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

                # -------------------------------------------------
                # Final confidence score
                # -------------------------------------------------

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

                # -------------------------------------------------
                # Risk level
                # -------------------------------------------------

                base_risk = ai_result.get(
                    "risk_level",
                    "safe",
                )

                comp_risk = comparison_result.get(
                    "risk_level",
                    "safe",
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

                # -------------------------------------------------
                # Save AI flag
                # -------------------------------------------------

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

                # -------------------------------------------------
                # Save AI analysis report
                # -------------------------------------------------

                self.submission_repo.save_ai_analysis_report(
                    submission_id=(
                        submission.id
                    ),
                    ai_flag_id=(
                        saved_flag.id
                    ),
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
                # AI detection is optional.
                # Submission creation must still succeed.
                pass

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

        # -----------------------------------------------------
        # Get submission
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Check ownership
        # -----------------------------------------------------

        if submission.user_id != user_id:
            raise PermissionError(
                "Forbidden"
            )

        # -----------------------------------------------------
        # Only draft can be edited
        # -----------------------------------------------------

        if submission.status != "draft":
            raise ValueError(
                "Cannot edit submission that is not in draft status"
            )

        # -----------------------------------------------------
        # Upload new files
        # -----------------------------------------------------

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

                files_data.append(
                    {
                        "image_hd_url": (
                            storage_info["hd_url"]
                        ),
                        "thumbnail_url": (
                            storage_info[
                                "thumbnail_url"
                            ]
                        ),
                        "file_hash": (
                            storage_info["sha256"]
                        ),
                        "width_px": (
                            storage_info["width"]
                        ),
                        "height_px": (
                            storage_info["height"]
                        ),
                        "file_size_bytes": (
                            storage_info["file_size"]
                        ),
                    }
                )

        # -----------------------------------------------------
        # Update repository
        #
        # IMPORTANT:
        # Pass user_id so repository can also
        # verify ownership.
        # -----------------------------------------------------

        return (
            self.submission_repo
            .update_draft(
                submission_id=(
                    submission_id
                ),
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

        # -----------------------------------------------------
        # Get submission with details
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Check ownership
        # -----------------------------------------------------

        if submission.user_id != user_id:
            raise PermissionError(
                "Forbidden"
            )

        # -----------------------------------------------------
        # Only draft can be submitted
        # -----------------------------------------------------

        if submission.status != "draft":
            raise ValueError(
                "Cannot submit submission that is not in draft status"
            )

        # -----------------------------------------------------
        # Validate title
        # -----------------------------------------------------

        if (
            not submission.title
            or not submission.title.strip()
        ):
            raise ValueError(
                "title is required"
            )

        # -----------------------------------------------------
        # Validate file
        # -----------------------------------------------------

        if not submission_file:
            raise ValueError(
                "At least one image file is required"
            )

        # -----------------------------------------------------
        # Validate film metadata
        # -----------------------------------------------------

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

        # =====================================================
        # AI DETECTION
        #
        # AI failure MUST NOT block official submission.
        # =====================================================

        if (
            submission_file
            and submission_file.image_hd_url
        ):

            try:

                try:
                    from services.ai_detection_service import (
                        AiDetectionService,
                    )
                except ImportError:
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

                ai_score = (
                    ai_result.get(
                        "ai_score",
                        0,
                    )
                )

                risk_level = (
                    ai_result.get(
                        "risk_level",
                        "safe",
                    )
                )

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
                    submission_id=(
                        submission.id
                    ),
                    ai_flag_id=(
                        saved_flag.id
                    ),
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
                    },
                )

            except Exception:
                # AI failure must not block submission.
                pass

        return updated_submission

    # =========================================================
    # GET SUBMISSION DETAIL
    # =========================================================

    def get_submission_by_id(
        self,
        submission_id: int,
    ) -> Optional[
        Tuple[
            SubmissionModel,
            Optional[
                SubmissionFileModel
            ],
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
    # ROLE-BASED SUBMISSION LISTING & FORMATTING
    # =========================================================

    def _format_submission_dict(
        self,
        submission: SubmissionModel,
        submission_file: Optional[SubmissionFileModel] = None,
        film_metadata: Optional[SubmissionFilmMetadataModel] = None,
        ai_flag: Optional[AIFlagModel] = None,
    ) -> Dict[str, Any]:
        item = {
            "id": submission.id,
            "round_id": submission.round_id,
            "user_id": submission.user_id,
            "title": submission.title,
            "story_description": submission.story_description,
            "status": submission.status,
            "final_score": (
                float(submission.final_score)
                if submission.final_score is not None
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
            "ai_flag": None,
        }

        if submission_file:
            item["file"] = {
                "id": submission_file.id,
                "image_hd_url": submission_file.image_hd_url,
                "thumbnail_url": submission_file.thumbnail_url,
                "width_px": submission_file.width_px,
                "height_px": submission_file.height_px,
                "file_size_bytes": submission_file.file_size_bytes,
                "file_hash": submission_file.file_hash,
                "created_at": (
                    submission_file.created_at.isoformat()
                    if submission_file.created_at
                    else None
                ),
            }

        if film_metadata:
            item["film_metadata"] = {
                "film_stock": film_metadata.film_stock,
                "film_iso": film_metadata.film_iso,
                "camera_body": film_metadata.camera_body,
                "lens": film_metadata.lens,
                "lab_name": film_metadata.lab_name,
                "scanner_info": film_metadata.scanner_info,
                "development_process": film_metadata.development_process,
                "taken_at_location": film_metadata.taken_at_location,
                "created_at": (
                    film_metadata.created_at.isoformat()
                    if film_metadata.created_at
                    else None
                ),
            }

        if ai_flag:
            item["ai_flag"] = {
                "ai_score": (
                    float(ai_flag.confidence_score)
                    if ai_flag.confidence_score is not None
                    else None
                ),
                "risk_level": ai_flag.risk_level,
                "status": ai_flag.status,
            }

        return item

    def get_my_submissions(
        self,
        user_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ) -> Dict[str, Any]:
        rows = self.submission_repo.get_participant_submissions(
            user_id=user_id,
            round_id=round_id,
            status=status,
            ai_flag=ai_flag,
        )
        submissions = [
            self._format_submission_dict(sub, file_obj, meta_obj, ai_obj)
            for sub, file_obj, meta_obj, ai_obj in rows
        ]
        return {
            "submissions": submissions,
            "total": len(submissions),
        }

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
            self.submission_repo.session.query(ContestModel)
            .filter_by(id=contest_id)
            .first()
        )
        if not contest:
            raise ValueError("Contest not found")

        if user_role != "admin" and contest.created_by != user_id:
            raise PermissionError("Forbidden")

        rows = self.submission_repo.get_organizer_submissions(
            contest_id=contest_id,
            round_id=round_id,
            status=status,
            ai_flag=ai_flag,
        )
        submissions = [
            self._format_submission_dict(sub, file_obj, meta_obj, ai_obj)
            for sub, file_obj, meta_obj, ai_obj in rows
        ]
        return {
            "submissions": submissions,
            "total": len(submissions),
        }

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
            self.submission_repo.session.query(JudgeAssignmentModel)
            .filter_by(id=assignment_id)
            .first()
        )
        if not assignment:
            raise ValueError("Assignment not found")

        if user_role != "admin" and assignment.judge_id != user_id:
            raise PermissionError("Forbidden")

        rows = self.submission_repo.get_judge_assignment_submissions(
            assignment_id=assignment_id,
            round_id=round_id,
            status=status,
            ai_flag=ai_flag,
        )
        if rows is None:
            raise ValueError("Assignment not found")

        submissions = [
            self._format_submission_dict(sub, file_obj, meta_obj, ai_obj)
            for sub, file_obj, meta_obj, ai_obj in rows
        ]
        return {
            "submissions": submissions,
            "total": len(submissions),
        }