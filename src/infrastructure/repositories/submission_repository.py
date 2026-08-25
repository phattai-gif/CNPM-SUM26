from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from domain.models.isubmission_repository import ISubmissionRepository
from domain.models.submission import Submission

from infrastructure.databases.factory_database import (
    FactoryDatabase as db_factory,
)

from infrastructure.models.app import (
    SubmissionModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
    AIFlagModel,
    AIAnalysisReportModel,
    RoundModel,

    ContestModel,
    JudgeAssignmentModel,
    ScoreModel,
    ScoreFeedbackModel,
    CriteriaModel,

    JudgeAssignmentModel,

)


class SubmissionRepository(ISubmissionRepository):

    def __init__(
        self,
        session: Optional[Session] = None,
    ):
        self.session = (
            session
            or db_factory.get_database("POSTGREE").session
        )

    # =========================================================
    # ADD
    # =========================================================

    def add(
        self,
        submission: Submission,
    ) -> SubmissionModel:

        try:
            model = SubmissionModel(
                round_id=submission.round_id,
                user_id=submission.user_id,
                title=submission.title,
                story_description=submission.story_description,
                status=submission.status,
                final_score=submission.final_score,
                submitted_at=submission.submitted_at,
                created_at=submission.created_at,
                updated_at=submission.updated_at,
            )

            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)

            return model

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # GET BY ID
    # =========================================================

    def get_by_id(
        self,
        submission_id: int,
    ) -> Optional[SubmissionModel]:

        return (
            self.session
            .query(SubmissionModel)
            .filter(
                SubmissionModel.id == submission_id
            )
            .first()
        )

    # =========================================================
    # GET BY ID WITH DETAILS
    # =========================================================

    def get_by_id_with_details(
        self,
        submission_id: int,
    ):
        """
        Return submission together with:
        - all submission files
        - film metadata

        Return:
            (
                submission,
                submission_files,
                film_metadata
            )
        """

        submission = (
            self.session
            .query(SubmissionModel)
            .filter(
                SubmissionModel.id == submission_id
            )
            .first()
        )

        if submission is None:
            return None

        submission_files = (
            self.session
            .query(SubmissionFileModel)
            .filter(
                SubmissionFileModel.submission_id
                == submission_id
            )
            .order_by(
                SubmissionFileModel.id.asc()
            )
            .all()
        )

        submission_film_metadata = (
            self.session
            .query(SubmissionFilmMetadataModel)
            .filter(
                SubmissionFilmMetadataModel.submission_id
                == submission_id
            )
            .first()
        )

        return (
            submission,
            submission_files,
            submission_film_metadata,
        )

    # =========================================================
    # LIST
    # =========================================================

    def list(
        self,
    ) -> List[SubmissionModel]:

        return (
            self.session
            .query(SubmissionModel)
            .order_by(
                SubmissionModel.id.desc()
            )
            .all()
        )

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        submission: Submission,
    ) -> SubmissionModel:

        try:
            model = (
                self.session
                .query(SubmissionModel)
                .filter(
                    SubmissionModel.id
                    == submission.id
                )
                .first()
            )

            if model is None:
                raise ValueError(
                    "Submission not found"
                )

            model.round_id = submission.round_id
            model.user_id = submission.user_id
            model.title = submission.title
            model.story_description = (
                submission.story_description
            )
            model.status = submission.status
            model.final_score = submission.final_score
            model.submitted_at = submission.submitted_at

            if submission.created_at is not None:
                model.created_at = submission.created_at

            if submission.updated_at is not None:
                model.updated_at = submission.updated_at

            self.session.commit()
            self.session.refresh(model)

            return model

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # DELETE
    # =========================================================

    def delete(
        self,
        submission_id: int,
    ) -> None:

        try:
            model = (
                self.session
                .query(SubmissionModel)
                .filter(
                    SubmissionModel.id
                    == submission_id
                )
                .first()
            )

            if model is None:
                raise ValueError(
                    "Submission not found"
                )

            self.session.delete(model)
            self.session.commit()

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # AI FLAG
    # =========================================================

    def save_ai_flag(
        self,
        submission_id: int,
        confidence_score: float,
        risk_level: str,
        flag_type: str = "AI_METADATA",
        status: str = "pending",
    ) -> AIFlagModel:

        try:
            existing = (
                self.session
                .query(AIFlagModel)
                .filter(
                    AIFlagModel.submission_id
                    == submission_id,
                    AIFlagModel.flag_type
                    == flag_type,
                )
                .first()
            )

            if existing:

                existing.confidence_score = (
                    confidence_score
                )
                existing.risk_level = risk_level
                existing.status = status

                self.session.commit()
                self.session.refresh(existing)

                return existing

            flag = AIFlagModel(
                submission_id=submission_id,
                flag_type=flag_type,
                confidence_score=confidence_score,
                risk_level=risk_level,
                status=status,
            )

            self.session.add(flag)
            self.session.commit()
            self.session.refresh(flag)

            return flag

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # GET AI FLAG
    # =========================================================

    def get_ai_flag(
        self,
        submission_id: int,
        flag_type: str = "AI_METADATA",
    ) -> Optional[AIFlagModel]:

        return (
            self.session
            .query(AIFlagModel)
            .filter(
                AIFlagModel.submission_id
                == submission_id,
                AIFlagModel.flag_type
                == flag_type,
            )
            .first()
        )

    # =========================================================
    # GET ALL AI FLAGS
    # =========================================================

    def get_all_ai_flags(
        self,
        submission_id: int,
    ) -> List[AIFlagModel]:

        return (
            self.session
            .query(AIFlagModel)
            .filter(
                AIFlagModel.submission_id
                == submission_id,
            )
            .order_by(
                AIFlagModel.id.asc()
            )
            .all()
        )

    # =========================================================
    # UPDATE AI FLAG STATUS
    # =========================================================

    def update_ai_flag_status(
        self,
        flag_id: int,
        status: str,
    ) -> Optional[AIFlagModel]:

        try:
            flag = (
                self.session
                .query(AIFlagModel)
                .filter(
                    AIFlagModel.id == flag_id
                )
                .first()
            )

            if not flag:
                return None

            flag.status = status

            self.session.commit()
            self.session.refresh(flag)

            return flag

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # GET FLAGGED SUBMISSIONS
    # =========================================================

    def get_flagged_submissions(
        self,
        status: Optional[str] = None,
    ) -> List[
        Tuple[
            SubmissionModel,
            Optional[SubmissionFileModel],
            Optional[SubmissionFilmMetadataModel],
            List[AIFlagModel],
        ]
    ]:

        query = (
            self.session
            .query(SubmissionModel)
            .join(
                AIFlagModel,
                AIFlagModel.submission_id
                == SubmissionModel.id,
            )
        )

        if status:
            query = query.filter(
                AIFlagModel.status == status
            )

        submissions = (
            query
            .order_by(
                SubmissionModel.submitted_at.desc(),
                SubmissionModel.id.desc(),
            )
            .distinct()
            .all()
        )

        results = []

        for submission in submissions:

            submission_files = (
                self.session
                .query(SubmissionFileModel)
                .filter(
                    SubmissionFileModel.submission_id
                    == submission.id
                )
                .order_by(
                    SubmissionFileModel.id.asc()
                )
                .all()
            )

            film_metadata = (
                self.session
                .query(
                    SubmissionFilmMetadataModel
                )
                .filter(
                    SubmissionFilmMetadataModel
                    .submission_id
                    == submission.id
                )
                .first()
            )

            ai_flags = (
                self.get_all_ai_flags(
                    submission.id
                )
            )

            results.append(
                (
                    submission,
                    submission_files,
                    film_metadata,
                    ai_flags,
                )
            )

        return results

    # =========================================================
    # AI ANALYSIS REPORT
    # =========================================================

    def save_ai_analysis_report(
        self,
        submission_id: int,
        ai_flag_id: Optional[int],
        ai_model_name: str,
        ai_confidence_score: float,
        raw_details: dict,
        similarity_matched_submission_id: Optional[int] = None,
    ) -> AIAnalysisReportModel:

        try:

            existing = (
                self.session
                .query(AIAnalysisReportModel)
                .filter(
                    AIAnalysisReportModel.submission_id
                    == submission_id,
                    AIAnalysisReportModel.ai_model_name
                    == ai_model_name,
                )
                .first()
            )

            if existing:

                existing.ai_flag_id = ai_flag_id

                existing.ai_confidence_score = (
                    ai_confidence_score
                )

                existing.raw_details = raw_details

                if hasattr(
                    existing,
                    "similarity_matched_submission_id",
                ):
                    existing.similarity_matched_submission_id = (
                        similarity_matched_submission_id
                    )

                self.session.commit()
                self.session.refresh(existing)

                return existing

            report_kwargs = {
                "submission_id": submission_id,
                "ai_flag_id": ai_flag_id,
                "ai_model_name": ai_model_name,
                "ai_confidence_score": (
                    ai_confidence_score
                ),
                "raw_details": raw_details,
            }

            if hasattr(
                AIAnalysisReportModel,
                "similarity_matched_submission_id",
            ):
                report_kwargs[
                    "similarity_matched_submission_id"
                ] = similarity_matched_submission_id

            report = AIAnalysisReportModel(
                **report_kwargs
            )

            self.session.add(report)
            self.session.commit()
            self.session.refresh(report)

            return report

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # CREATE SUBMISSION
    # =========================================================

    def create_submission(
        self,
        round_id: int,
        user_id: int,
        title: str = "",
        image_hd_url: Optional[str] = None,
        file_hash: Optional[str] = None,
        story_description: str = "",
        thumbnail_url: Optional[str] = None,
        width_px: Optional[int] = None,
        height_px: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        files_data: Optional[List[dict]] = None,
        film_stock: str = "",
        film_iso: Optional[int] = None,
        camera_body: Optional[str] = None,
        lens: Optional[str] = None,
        lab_name: Optional[str] = None,
        scanner_info: Optional[str] = None,
        development_process: str = "C-41",
        taken_at_location: Optional[str] = None,
        status: str = "draft",
    ) -> SubmissionModel:

        try:

            # -------------------------------------------------
            # Check round
            # -------------------------------------------------

            round_obj = (
                self.session
                .query(RoundModel)
                .filter(
                    RoundModel.id == round_id
                )
                .first()
            )

            if not round_obj:
                raise ValueError(
                    f"Round with id {round_id} does not exist"
                )

            # -------------------------------------------------
            # Create submission
            # -------------------------------------------------

            submission = SubmissionModel(
                round_id=round_id,
                user_id=user_id,
                title=title or "",
                story_description=(
                    story_description or ""
                ),
                status=status,
            )

            self.session.add(submission)

            # Need ID for child records
            self.session.flush()

            # -------------------------------------------------
            # Prepare files
            # -------------------------------------------------

            file_list = []

            if files_data:
                file_list = files_data

            elif image_hd_url and file_hash:

                file_list = [
                    {
                        "file_type": "main_image",
                        "image_hd_url": image_hd_url,
                        "thumbnail_url": thumbnail_url,
                        "width_px": width_px,
                        "height_px": height_px,
                        "file_size_bytes": (
                            file_size_bytes
                        ),
                        "file_hash": file_hash,
                        "phash": None,
                        "ahash": None,
                    }
                ]

            # -------------------------------------------------
            # Create submission files
            # -------------------------------------------------

            for f_info in file_list:

                if not f_info.get(
                    "image_hd_url"
                ):
                    raise ValueError(
                        "image_hd_url is required"
                    )

                if not f_info.get(
                    "file_hash"
                ):
                    raise ValueError(
                        "file_hash is required"
                    )

                submission_file = (
                    SubmissionFileModel(
                        submission_id=(
                            submission.id
                        ),
                        image_hd_url=(
                            f_info[
                                "image_hd_url"
                            ]
                        ),
                        thumbnail_url=(
                            f_info.get(
                                "thumbnail_url"
                            )
                        ),
                        width_px=(
                            f_info.get(
                                "width_px"
                            )
                        ),
                        height_px=(
                            f_info.get(
                                "height_px"
                            )
                        ),
                        file_size_bytes=(
                            f_info.get(
                                "file_size_bytes"
                            )
                        ),
                        file_hash=(
                            f_info[
                                "file_hash"
                            ]
                        ),
                        phash=f_info.get(
                            "phash"
                        ),
                        ahash=f_info.get(
                            "ahash"
                        ),
                        file_type=f_info.get(
                            "file_type",
                            "main_image",
                        ),
                    )
                )

                self.session.add(
                    submission_file
                )

            # -------------------------------------------------
            # Create film metadata
            # -------------------------------------------------

            film_metadata = (
                SubmissionFilmMetadataModel(
                    submission_id=submission.id,
                    film_stock=(
                        film_stock or ""
                    ),
                    film_iso=film_iso,
                    camera_body=camera_body,
                    lens=lens,
                    lab_name=lab_name,
                    scanner_info=scanner_info,
                    development_process=(
                        development_process
                        or "C-41"
                    ),
                    taken_at_location=(
                        taken_at_location
                    ),
                )
            )

            self.session.add(
                film_metadata
            )

            # -------------------------------------------------
            # Commit
            # -------------------------------------------------

            self.session.commit()
            self.session.refresh(submission)

            return submission

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # UPDATE DRAFT
    # =========================================================

    def update_draft(
        self,
        submission_id: int,
        user_id: Optional[int] = None,
        title: Optional[str] = None,
        story_description: Optional[str] = None,
        files_data: Optional[List[dict]] = None,
        film_metadata: Optional[dict] = None,
    ) -> SubmissionModel:

        try:

            query = (
                self.session
                .query(SubmissionModel)
                .filter(
                    SubmissionModel.id
                    == submission_id
                )
            )

            if user_id is not None:
                query = query.filter(
                    SubmissionModel.user_id
                    == user_id
                )

            submission = query.first()

            if not submission:
                raise ValueError(
                    "Submission not found"
                )

            if submission.status != "draft":
                raise PermissionError(
                    "Only draft submissions can be updated"
                )

            # -------------------------------------------------
            # Basic information
            # -------------------------------------------------

            if title is not None:
                submission.title = title

            if story_description is not None:
                submission.story_description = (
                    story_description
                )

            # -------------------------------------------------
            # Add files
            # -------------------------------------------------

            if files_data:

                for f_info in files_data:

                    if not f_info.get(
                        "image_hd_url"
                    ):
                        raise ValueError(
                            "image_hd_url is required"
                        )

                    if not f_info.get(
                        "file_hash"
                    ):
                        raise ValueError(
                            "file_hash is required"
                        )

                    submission_file = (
                        SubmissionFileModel(
                            submission_id=(
                                submission.id
                            ),
                            image_hd_url=(
                                f_info[
                                    "image_hd_url"
                                ]
                            ),
                            thumbnail_url=(
                                f_info.get(
                                    "thumbnail_url"
                                )
                            ),
                            width_px=(
                                f_info.get(
                                    "width_px"
                                )
                            ),
                            height_px=(
                                f_info.get(
                                    "height_px"
                                )
                            ),
                            file_size_bytes=(
                                f_info.get(
                                    "file_size_bytes"
                                )
                            ),
                            file_hash=(
                                f_info[
                                    "file_hash"
                                ]
                            ),
                            phash=f_info.get(
                                "phash"
                            ),
                            ahash=f_info.get(
                                "ahash"
                            ),
                            file_type=f_info.get(
                                "file_type",
                                "main_image",
                            ),
                        )
                    )

                    self.session.add(
                        submission_file
                    )

            # -------------------------------------------------
            # Film metadata
            # -------------------------------------------------

            if film_metadata is not None:

                meta_obj = (
                    self.session
                    .query(
                        SubmissionFilmMetadataModel
                    )
                    .filter(
                        SubmissionFilmMetadataModel
                        .submission_id
                        == submission_id
                    )
                    .first()
                )

                if not meta_obj:

                    meta_obj = (
                        SubmissionFilmMetadataModel(
                            submission_id=(
                                submission.id
                            ),
                            film_stock=(
                                film_metadata.get(
                                    "film_stock"
                                )
                                or ""
                            ),
                            development_process=(
                                film_metadata.get(
                                    "development_process"
                                )
                                or "C-41"
                            ),
                        )
                    )

                    self.session.add(
                        meta_obj
                    )

                if "film_stock" in film_metadata:
                    meta_obj.film_stock = (
                        film_metadata[
                            "film_stock"
                        ]
                        or ""
                    )

                if "film_iso" in film_metadata:
                    meta_obj.film_iso = (
                        film_metadata[
                            "film_iso"
                        ]
                    )

                if "camera_body" in film_metadata:
                    meta_obj.camera_body = (
                        film_metadata[
                            "camera_body"
                        ]
                    )

                if "lens" in film_metadata:
                    meta_obj.lens = (
                        film_metadata[
                            "lens"
                        ]
                    )

                if "lab_name" in film_metadata:
                    meta_obj.lab_name = (
                        film_metadata[
                            "lab_name"
                        ]
                    )

                if "scanner_info" in film_metadata:
                    meta_obj.scanner_info = (
                        film_metadata[
                            "scanner_info"
                        ]
                    )

                if "development_process" in film_metadata:
                    meta_obj.development_process = (
                        film_metadata[
                            "development_process"
                        ]
                        or "C-41"
                    )

                if "taken_at_location" in film_metadata:
                    meta_obj.taken_at_location = (
                        film_metadata[
                            "taken_at_location"
                        ]
                    )

            # -------------------------------------------------
            # Commit
            # -------------------------------------------------

            self.session.commit()
            self.session.refresh(submission)

            return submission

        except Exception:
            self.session.rollback()
            raise

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
        film_metadata: Optional[dict] = None,
        image_hd_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        file_hash: Optional[str] = None,
        width_px: Optional[int] = None,
        height_px: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        file_type: str = "main_image",
    ) -> SubmissionModel:

        try:

            # -------------------------------------------------
            # Find submission
            # -------------------------------------------------

            submission = (
                self.session
                .query(SubmissionModel)
                .filter(
                    SubmissionModel.id
                    == submission_id,
                    SubmissionModel.user_id
                    == user_id,
                )
                .first()
            )

            if not submission:
                raise ValueError(
                    "Submission not found"
                )

            # -------------------------------------------------
            # Only draft can be edited
            # -------------------------------------------------

            if submission.status != "draft":
                raise PermissionError(
                    "Only draft submissions can be updated"
                )

            # -------------------------------------------------
            # Basic fields
            # -------------------------------------------------

            if title is not None:
                submission.title = title

            if story_description is not None:
                submission.story_description = (
                    story_description
                )

            if round_id is not None:
                round_obj = (
                    self.session
                    .query(RoundModel)
                    .filter(
                        RoundModel.id
                        == round_id
                    )
                    .first()
                )

                if not round_obj:
                    raise ValueError(
                        f"Round with id {round_id} does not exist"
                    )

                submission.round_id = round_id

            # -------------------------------------------------
            # Status
            # -------------------------------------------------

            if status is not None:
                submission.status = status

            # -------------------------------------------------
            # Update file
            # -------------------------------------------------

            if image_hd_url:

                normalized_file_type = (
                    file_type
                    or "main_image"
                )

                existing_file = (
                    self.session
                    .query(
                        SubmissionFileModel
                    )
                    .filter(
                        SubmissionFileModel
                        .submission_id
                        == submission_id,
                        SubmissionFileModel
                        .file_type
                        == normalized_file_type,
                    )
                    .first()
                )

                if existing_file:

                    existing_file.image_hd_url = (
                        image_hd_url
                    )

                    if thumbnail_url is not None:
                        existing_file.thumbnail_url = (
                            thumbnail_url
                        )

                    if file_hash is not None:
                        existing_file.file_hash = (
                            file_hash
                        )

                    if width_px is not None:
                        existing_file.width_px = (
                            width_px
                        )

                    if height_px is not None:
                        existing_file.height_px = (
                            height_px
                        )

                    if file_size_bytes is not None:
                        existing_file.file_size_bytes = (
                            file_size_bytes
                        )

                    existing_file.file_type = (
                        normalized_file_type
                    )

                else:

                    if not file_hash:
                        raise ValueError(
                            "file_hash is required when adding a new submission file"
                        )

                    submission_file = (
                        SubmissionFileModel(
                            submission_id=(
                                submission.id
                            ),
                            image_hd_url=(
                                image_hd_url
                            ),
                            thumbnail_url=(
                                thumbnail_url
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
                            file_hash=(
                                file_hash
                            ),
                            phash=None,
                            ahash=None,
                            file_type=(
                                normalized_file_type
                            ),
                        )
                    )

                    self.session.add(
                        submission_file
                    )

            # -------------------------------------------------
            # Film metadata
            # -------------------------------------------------

            if film_metadata is not None:

                meta_obj = (
                    self.session
                    .query(
                        SubmissionFilmMetadataModel
                    )
                    .filter(
                        SubmissionFilmMetadataModel
                        .submission_id
                        == submission_id
                    )
                    .first()
                )

                if not meta_obj:

                    meta_obj = (
                        SubmissionFilmMetadataModel(
                            submission_id=(
                                submission.id
                            ),
                            film_stock="",
                            development_process="C-41",
                        )
                    )

                    self.session.add(
                        meta_obj
                    )

                if "film_stock" in film_metadata:
                    meta_obj.film_stock = (
                        film_metadata.get(
                            "film_stock"
                        )
                        or ""
                    )

                if "film_iso" in film_metadata:
                    meta_obj.film_iso = (
                        film_metadata.get(
                            "film_iso"
                        )
                    )

                if "camera_body" in film_metadata:
                    meta_obj.camera_body = (
                        film_metadata.get(
                            "camera_body"
                        )
                    )

                if "lens" in film_metadata:
                    meta_obj.lens = (
                        film_metadata.get(
                            "lens"
                        )
                    )

                if "lab_name" in film_metadata:
                    meta_obj.lab_name = (
                        film_metadata.get(
                            "lab_name"
                        )
                    )

                if "scanner_info" in film_metadata:
                    meta_obj.scanner_info = (
                        film_metadata.get(
                            "scanner_info"
                        )
                    )

                if "development_process" in film_metadata:
                    meta_obj.development_process = (
                        film_metadata.get(
                            "development_process"
                        )
                        or "C-41"
                    )

                if "taken_at_location" in film_metadata:
                    meta_obj.taken_at_location = (
                        film_metadata.get(
                            "taken_at_location"
                        )
                    )

            # -------------------------------------------------
            # Commit
            # -------------------------------------------------

            self.session.commit()
            self.session.refresh(submission)

            return submission

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # UPDATE STATUS
    # =========================================================

    def update_status(
        self,
        submission_id: int,
        status: str,
        submitted_at=None,
    ) -> SubmissionModel:

        try:

            submission = (
                self.session
                .query(SubmissionModel)
                .filter(
                    SubmissionModel.id
                    == submission_id
                )
                .first()
            )

            if not submission:
                raise ValueError(
                    "Submission not found"
                )

            submission.status = status

            if submitted_at is not None:
                submission.submitted_at = (
                    submitted_at
                )

            self.session.commit()
            self.session.refresh(submission)

            return submission

        except Exception:
            self.session.rollback()
            raise

    # =========================================================
    # ENRICH SUBMISSIONS
    # =========================================================

    def _enrich_submissions_with_details(
        self,
        submissions: List[SubmissionModel],
    ):

        results = []

        for submission in submissions:

            submission_files = (
                self.session
                .query(SubmissionFileModel)
                .filter(
                    SubmissionFileModel.submission_id
                    == submission.id
                )
                .order_by(
                    SubmissionFileModel.id.asc()
                )
                .all()
            )

            film_metadata = (
                self.session
                .query(
                    SubmissionFilmMetadataModel
                )
                .filter(
                    SubmissionFilmMetadataModel
                    .submission_id
                    == submission.id
                )
                .first()
            )

            ai_flags = (
                self.get_all_ai_flags(
                    submission.id
                )
            )

            results.append(
                (
                    submission,
                    submission_files,
                    film_metadata,
                    ai_flags,
                )
            )

        return results

    # =========================================================
    # PARTICIPANT SUBMISSIONS
    # =========================================================

    def get_participant_submissions(
        self,
        user_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ):

        query = (
            self.session
            .query(SubmissionModel)
            .filter(
                SubmissionModel.user_id
                == user_id
            )
        )

        if round_id is not None:
            query = query.filter(
                SubmissionModel.round_id
                == round_id
            )

        if status:
            query = query.filter(
                SubmissionModel.status
                == status
            )

        if ai_flag:
            query = (
                query
                .join(
                    AIFlagModel,
                    AIFlagModel.submission_id
                    == SubmissionModel.id,
                )
                .filter(
                    AIFlagModel.risk_level
                    == ai_flag
                )
            )

        submissions = (
            query
            .order_by(
                SubmissionModel.submitted_at.desc(),
                SubmissionModel.id.desc(),
            )
            .distinct()
            .all()
        )

        return (
            self._enrich_submissions_with_details(
                submissions
            )
        )

    # =========================================================
    # ORGANIZER SUBMISSIONS
    # =========================================================

    def get_organizer_submissions(
        self,
        contest_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ):

        query = (
            self.session
            .query(SubmissionModel)
            .join(
                RoundModel,
                SubmissionModel.round_id
                == RoundModel.id,
            )
            .filter(
                RoundModel.contest_id
                == contest_id
            )
        )

        if round_id is not None:
            query = query.filter(
                SubmissionModel.round_id
                == round_id
            )

        if status:
            query = query.filter(
                SubmissionModel.status
                == status
            )

        if ai_flag:
            query = (
                query
                .join(
                    AIFlagModel,
                    AIFlagModel.submission_id
                    == SubmissionModel.id,
                )
                .filter(
                    AIFlagModel.risk_level
                    == ai_flag
                )
            )

        submissions = (
            query
            .order_by(
                SubmissionModel.submitted_at.desc(),
                SubmissionModel.id.desc(),
            )
            .distinct()
            .all()
        )

        return (
            self._enrich_submissions_with_details(
                submissions
            )
        )

    # =========================================================
    # JUDGE ASSIGNMENT SUBMISSIONS
    # =========================================================

    def get_judge_assignment_submissions(
        self,
        assignment_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ):

        assignment = (
            self.session
            .query(JudgeAssignmentModel)
            .filter(
                JudgeAssignmentModel.id
                == assignment_id
            )
            .first()
        )

        if not assignment:
            return None

        # -------------------------------------------------
        # Assignment points to one submission
        # -------------------------------------------------

        if assignment.submission_id is not None:

            query = (
                self.session
                .query(SubmissionModel)
                .filter(
                    SubmissionModel.id
                    == assignment.submission_id
                )
            )

        # -------------------------------------------------
        # Assignment points to a round
        # -------------------------------------------------

        else:

            query = (
                self.session
                .query(SubmissionModel)
                .filter(
                    SubmissionModel.round_id
                    == assignment.round_id
                )
            )

        if round_id is not None:
            query = query.filter(
                SubmissionModel.round_id
                == round_id
            )

        if status:
            query = query.filter(
                SubmissionModel.status
                == status
            )

        if ai_flag:
            query = (
                query
                .join(
                    AIFlagModel,
                    AIFlagModel.submission_id
                    == SubmissionModel.id,
                )
                .filter(
                    AIFlagModel.risk_level
                    == ai_flag
                )
            )

        submissions = (
            query
            .order_by(
                SubmissionModel.submitted_at.desc(),
                SubmissionModel.id.desc(),
            )
            .distinct()
            .all()
        )

        return (
            self._enrich_submissions_with_details(
                submissions
            )
        )