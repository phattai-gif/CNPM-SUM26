from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from domain.models.isubmission_repository import ISubmissionRepository
from domain.models.submission import Submission

from infrastructure.databases.factory_database import (
    FactoryDatabase as db_factory
)
try:
    from infrastructure.models.app import (
        SubmissionModel,
        SubmissionFileModel,
        SubmissionFilmMetadataModel,
        AIFlagModel,
        AIAnalysisReportModel,
        RoundModel,
        ContestModel,
        JudgeAssignmentModel,
    )
except ImportError:
    from infrastructure.models.app import (
        SubmissionModel,
        SubmissionFileModel,
        SubmissionFilmMetadataModel,
        AIFlagModel,
        AIAnalysisReportModel,
        RoundModel,
        ContestModel,
        JudgeAssignmentModel,
    )
from infrastructure.models.app import (
    SubmissionModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
    AIFlagModel,
    AIAnalysisReportModel,
    RoundModel,
)


class SubmissionRepository(ISubmissionRepository):

    def __init__(self, session: Optional[Session] = None):
        self.session = (
            session
            or db_factory.get_database("POSTGREE").session
        )

    # =========================================================
    # ADD
    # =========================================================

    def add(
        self,
        submission: Submission
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
        submission_id: int
    ) -> Optional[SubmissionModel]:

        return (
            self.session
            .query(SubmissionModel)
            .filter_by(id=submission_id)
            .first()
        )

    # =========================================================
    # GET BY ID WITH DETAILS
    # =========================================================

    def get_by_id_with_details(
        self,
        submission_id: int
    ) -> Optional[
        Tuple[
            SubmissionModel,
            Optional[SubmissionFileModel],
            Optional[SubmissionFilmMetadataModel],
        ]
    ]:

        submission = (
            self.session
            .query(SubmissionModel)
            .filter_by(id=submission_id)
            .first()
        )

        if submission is None:
            return None

        submission_file = (
            self.session
            .query(SubmissionFileModel)
            .filter_by(
                submission_id=submission_id
            )
            .first()
        )

        submission_film_metadata = (
            self.session
            .query(SubmissionFilmMetadataModel)
            .filter_by(
                submission_id=submission_id
            )
            .first()
        )

        return (
            submission,
            submission_file,
            submission_film_metadata,
        )

    # =========================================================
    # LIST
    # =========================================================

    def list(
        self
    ) -> List[SubmissionModel]:

        return (
            self.session
            .query(SubmissionModel)
            .all()
        )

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        submission: Submission
    ) -> SubmissionModel:

        try:
            model = (
                self.session
                .query(SubmissionModel)
                .filter_by(
                    id=submission.id
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
            model.created_at = submission.created_at
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
        submission_id: int
    ) -> None:

        try:
            model = (
                self.session
                .query(SubmissionModel)
                .filter_by(
                    id=submission_id
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
        """
        Save or update AI warning flag
        for a submission.
        """

        try:
            existing = (
                self.session
                .query(AIFlagModel)
                .filter_by(
                    submission_id=submission_id,
                    flag_type=flag_type,
                )
                .first()
            )

            # Existing flag -> update
            if existing:

                existing.confidence_score = (
                    confidence_score
                )

                existing.risk_level = (
                    risk_level
                )

                existing.status = status

                self.session.commit()
                self.session.refresh(existing)

                return existing

            # Create new flag
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
        """
        Retrieve AI warning flag
        of a submission.
        """

        return (
            self.session
            .query(AIFlagModel)
            .filter_by(
                submission_id=submission_id,
                flag_type=flag_type,
            )
            .first()
        )

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
    ) -> AIAnalysisReportModel:
        """
        Save or update AI analysis report
        for a submission.
        """

        try:
            existing = (
                self.session
                .query(AIAnalysisReportModel)
                .filter_by(
                    submission_id=submission_id,
                    ai_model_name=ai_model_name,
                )
                .first()
            )

            # Existing report -> update
            if existing:

                existing.ai_flag_id = (
                    ai_flag_id
                )

                existing.ai_confidence_score = (
                    ai_confidence_score
                )

                existing.raw_details = (
                    raw_details
                )

                self.session.commit()
                self.session.refresh(existing)

                return existing

            # Create new report
            report = AIAnalysisReportModel(
                submission_id=submission_id,
                ai_flag_id=ai_flag_id,
                ai_model_name=ai_model_name,
                ai_confidence_score=ai_confidence_score,
                raw_details=raw_details,
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
                .filter_by(
                    id=round_id
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

            # Get submission.id before creating
            # related records
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
                        "image_hd_url": image_hd_url,
                        "thumbnail_url": thumbnail_url,
                        "width_px": width_px,
                        "height_px": height_px,
                        "file_size_bytes": file_size_bytes,
                        "file_hash": file_hash,
                    }
                ]

            # -------------------------------------------------
            # Create submission files
            # -------------------------------------------------

            for f_info in file_list:

                submission_file = SubmissionFileModel(
                    submission_id=submission.id,
                    image_hd_url=f_info[
                        "image_hd_url"
                    ],
                    thumbnail_url=f_info.get(
                        "thumbnail_url"
                    ),
                    width_px=f_info.get(
                        "width_px"
                    ),
                    height_px=f_info.get(
                        "height_px"
                    ),
                    file_size_bytes=f_info.get(
                        "file_size_bytes"
                    ),
                    file_hash=f_info[
                        "file_hash"
                    ],
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

            # -------------------------------------------------
            # Find submission
            # -------------------------------------------------

            query = (
                self.session
                .query(SubmissionModel)
                .filter_by(
                    id=submission_id
                )
            )

            # -------------------------------------------------
            # Check ownership when user_id is provided
            #
            # This keeps backward compatibility with
            # old tasks that may call update_draft()
            # without user_id.
            # -------------------------------------------------

            if user_id is not None:
                query = query.filter_by(
                    user_id=user_id
                )

            submission = query.first()

            if not submission:
                raise ValueError(
                    "Submission not found"
                )

            # -------------------------------------------------
            # Only draft can be updated
            # -------------------------------------------------

            if submission.status != "draft":
                raise PermissionError(
                    "Only draft submissions can be updated"
                )

            # -------------------------------------------------
            # Update basic information
            # -------------------------------------------------

            if title is not None:
                submission.title = title

            if story_description is not None:
                submission.story_description = (
                    story_description
                )

            # -------------------------------------------------
            # Add new files
            # -------------------------------------------------

            if files_data:

                for f_info in files_data:

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
                        )
                    )

                    self.session.add(
                        submission_file
                    )

            # -------------------------------------------------
            # Update film metadata
            # -------------------------------------------------

            if film_metadata is not None:

                meta_obj = (
                    self.session
                    .query(
                        SubmissionFilmMetadataModel
                    )
                    .filter_by(
                        submission_id=submission_id
                    )
                    .first()
                )

                # Create metadata if not exists
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
                        )
                    )

                    self.session.add(
                        meta_obj
                    )

                # film_stock
                if (
                    "film_stock"
                    in film_metadata
                ):
                    meta_obj.film_stock = (
                        film_metadata[
                            "film_stock"
                        ]
                        or ""
                    )

                # film_iso
                if (
                    "film_iso"
                    in film_metadata
                ):
                    meta_obj.film_iso = (
                        film_metadata[
                            "film_iso"
                        ]
                    )

                # camera_body
                if (
                    "camera_body"
                    in film_metadata
                ):
                    meta_obj.camera_body = (
                        film_metadata[
                            "camera_body"
                        ]
                    )

                # lens
                if "lens" in film_metadata:
                    meta_obj.lens = (
                        film_metadata[
                            "lens"
                        ]
                    )

                # lab_name
                if (
                    "lab_name"
                    in film_metadata
                ):
                    meta_obj.lab_name = (
                        film_metadata[
                            "lab_name"
                        ]
                    )

                # scanner_info
                if (
                    "scanner_info"
                    in film_metadata
                ):
                    meta_obj.scanner_info = (
                        film_metadata[
                            "scanner_info"
                        ]
                    )

                # development_process
                if (
                    "development_process"
                    in film_metadata
                ):
                    meta_obj.development_process = (
                        film_metadata[
                            "development_process"
                        ]
                        or "C-41"
                    )

                # taken_at_location
                if (
                    "taken_at_location"
                    in film_metadata
                ):
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
                .filter_by(
                    id=submission_id
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
    # ROLE-BASED LIST SUBMISSIONS & FILTERS
    # =========================================================

    def _enrich_submissions_with_details(
        self, submissions: List[SubmissionModel]
    ) -> List[Tuple[SubmissionModel, Optional[SubmissionFileModel], Optional[SubmissionFilmMetadataModel], Optional[AIFlagModel]]]:
        results = []
        for sub in submissions:
            sub_file = (
                self.session.query(SubmissionFileModel)
                .filter_by(submission_id=sub.id)
                .first()
            )
            sub_meta = (
                self.session.query(SubmissionFilmMetadataModel)
                .filter_by(submission_id=sub.id)
                .first()
            )
            sub_ai = (
                self.session.query(AIFlagModel)
                .filter_by(submission_id=sub.id)
                .first()
            )
            results.append((sub, sub_file, sub_meta, sub_ai))
        return results

    def get_participant_submissions(
        self,
        user_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ) -> List[Tuple[SubmissionModel, Optional[SubmissionFileModel], Optional[SubmissionFilmMetadataModel], Optional[AIFlagModel]]]:
        query = self.session.query(SubmissionModel).filter(
            SubmissionModel.user_id == user_id
        )

        if round_id is not None:
            query = query.filter(SubmissionModel.round_id == round_id)

        if status:
            query = query.filter(SubmissionModel.status == status)

        if ai_flag:
            query = query.join(
                AIFlagModel, AIFlagModel.submission_id == SubmissionModel.id
            ).filter(AIFlagModel.risk_level == ai_flag)

        query = query.order_by(
            SubmissionModel.submitted_at.desc(), SubmissionModel.id.desc()
        )
        submissions = query.distinct().all()
        return self._enrich_submissions_with_details(submissions)

    def get_organizer_submissions(
        self,
        contest_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ) -> List[Tuple[SubmissionModel, Optional[SubmissionFileModel], Optional[SubmissionFilmMetadataModel], Optional[AIFlagModel]]]:
        query = (
            self.session.query(SubmissionModel)
            .join(RoundModel, SubmissionModel.round_id == RoundModel.id)
            .filter(RoundModel.contest_id == contest_id)
        )

        if round_id is not None:
            query = query.filter(SubmissionModel.round_id == round_id)

        if status:
            query = query.filter(SubmissionModel.status == status)

        if ai_flag:
            query = query.join(
                AIFlagModel, AIFlagModel.submission_id == SubmissionModel.id
            ).filter(AIFlagModel.risk_level == ai_flag)

        query = query.order_by(
            SubmissionModel.submitted_at.desc(), SubmissionModel.id.desc()
        )
        submissions = query.distinct().all()
        return self._enrich_submissions_with_details(submissions)

    def get_judge_assignment_submissions(
        self,
        assignment_id: int,
        round_id: Optional[int] = None,
        status: Optional[str] = None,
        ai_flag: Optional[str] = None,
    ) -> Optional[List[Tuple[SubmissionModel, Optional[SubmissionFileModel], Optional[SubmissionFilmMetadataModel], Optional[AIFlagModel]]]]:
        assignment = (
            self.session.query(JudgeAssignmentModel)
            .filter_by(id=assignment_id)
            .first()
        )
        if not assignment:
            return None

        if assignment.submission_id is not None:
            query = self.session.query(SubmissionModel).filter(
                SubmissionModel.id == assignment.submission_id
            )
        else:
            query = self.session.query(SubmissionModel).filter(
                SubmissionModel.round_id == assignment.round_id
            )

        if round_id is not None:
            query = query.filter(SubmissionModel.round_id == round_id)

        if status:
            query = query.filter(SubmissionModel.status == status)

        if ai_flag:
            query = query.join(
                AIFlagModel, AIFlagModel.submission_id == SubmissionModel.id
            ).filter(AIFlagModel.risk_level == ai_flag)

        query = query.order_by(
            SubmissionModel.submitted_at.desc(), SubmissionModel.id.desc()
        )
        submissions = query.distinct().all()
        return self._enrich_submissions_with_details(submissions)

        
        