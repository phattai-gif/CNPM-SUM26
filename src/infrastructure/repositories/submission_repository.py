from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from domain.models.isubmission_repository import ISubmissionRepository
from domain.models.submission import Submission
from infrastructure.databases.factory_database import (
    FactoryDatabase as db_factory
)
from infrastructure.models.app import (
    SubmissionModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
    AIFlagModel,
    AIAnalysisReportModel,
    RoundModel,
    ContestModel,
    ScoreModel,
    ScoreFeedbackModel,
    CriteriaModel,
)


class SubmissionRepository(ISubmissionRepository):

    def __init__(self, session: Optional[Session] = None):
        self.session = (
            session
            or db_factory.get_database("POSTGREE").session
        )

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

    def get_by_id_with_details(
        self,
        submission_id: int
    ) -> Optional[Tuple[SubmissionModel, Optional[SubmissionFileModel], Optional[SubmissionFilmMetadataModel]]]:

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
            .filter_by(submission_id=submission_id)
            .first()
        )

        submission_film_metadata = (
            self.session
            .query(SubmissionFilmMetadataModel)
            .filter_by(submission_id=submission_id)
            .first()
        )

        return submission, submission_file, submission_film_metadata

    def list(self) -> List[SubmissionModel]:

        return (
            self.session
            .query(SubmissionModel)
            .all()
        )

    def update(
        self,
        submission: Submission
    ) -> SubmissionModel:

        try:
            model = (
                self.session
                .query(SubmissionModel)
                .filter_by(id=submission.id)
                .first()
            )

            if model is None:
                raise ValueError("Submission not found")

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

    def delete(
        self,
        submission_id: int
    ) -> None:

        try:
            model = (
                self.session
                .query(SubmissionModel)
                .filter_by(id=submission_id)
                .first()
            )

            if model is None:
                raise ValueError("Submission not found")

            self.session.delete(model)
            self.session.commit()

        except Exception:
            self.session.rollback()
            raise


    def save_ai_flag(
        self,
        submission_id: int,
        confidence_score: float,
        risk_level: str,
        flag_type: str = "AI_METADATA",
        status: str = "pending",
    ) -> AIFlagModel:
        """Save or update AI warning flag for a submission into ai_flags table."""
        try:
            existing = (
                self.session
                .query(AIFlagModel)
                .filter_by(submission_id=submission_id, flag_type=flag_type)
                .first()
            )
            if existing:
                existing.confidence_score = confidence_score
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

    def get_ai_flag(
        self,
        submission_id: int,
        flag_type: str = "AI_METADATA",
    ) -> Optional[AIFlagModel]:
        """Retrieve AI warning flag information of a submission from DB."""
        return (
            self.session
            .query(AIFlagModel)
            .filter_by(submission_id=submission_id, flag_type=flag_type)
            .first()
        )

    def save_ai_analysis_report(
        self,
        submission_id: int,
        ai_flag_id: Optional[int],
        ai_model_name: str,
        ai_confidence_score: float,
        raw_details: dict,
    ) -> AIAnalysisReportModel:
        """Save or update AI analysis report for a submission into ai_analysis_reports table."""
        try:
            existing = (
                self.session
                .query(AIAnalysisReportModel)
                .filter_by(submission_id=submission_id, ai_model_name=ai_model_name)
                .first()
            )
            if existing:
                existing.ai_flag_id = ai_flag_id
                existing.ai_confidence_score = ai_confidence_score
                existing.raw_details = raw_details
                self.session.commit()
                self.session.refresh(existing)
                return existing

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

    def create_submission(
        self,
        round_id: int,
        user_id: int,
        title: str,
        image_hd_url: str,
        file_hash: str,
        story_description: str = "",
        thumbnail_url: Optional[str] = None,
        width_px: Optional[int] = None,
        height_px: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        film_stock: str = "",
        film_iso: Optional[int] = None,
        camera_body: Optional[str] = None,
        lens: Optional[str] = None,
        lab_name: Optional[str] = None,
        scanner_info: Optional[str] = None,
        development_process: str = "C-41",
        taken_at_location: Optional[str] = None,
        status: str = "submitted",
    ) -> SubmissionModel:

        try:

            submission = SubmissionModel(
                round_id=round_id,
                user_id=user_id,
                title=title,
                story_description=story_description,
                status=status,
            )

            self.session.add(submission)


            self.session.flush()

            submission_file = SubmissionFileModel(
                submission_id=submission.id,
                image_hd_url=image_hd_url,
                thumbnail_url=thumbnail_url,
                width_px=width_px,
                height_px=height_px,
                file_size_bytes=file_size_bytes,
                file_hash=file_hash,
            )

            self.session.add(submission_file)

            film_metadata = SubmissionFilmMetadataModel(
                submission_id=submission.id,
                film_stock=film_stock,
                film_iso=film_iso,
                camera_body=camera_body,
                lens=lens,
                lab_name=lab_name,
                scanner_info=scanner_info,
                development_process=development_process,
                taken_at_location=taken_at_location,
            )

            self.session.add(film_metadata)


            self.session.commit()
            self.session.refresh(submission)

            return submission

        except Exception:
            self.session.rollback()
            raise

    def get_my_submissions(self, user_id: int) -> List[dict]:
        """Fetch all submissions created by a specific user with contest, round, file, and AI flag info."""
        submissions = (
            self.session.query(SubmissionModel)
            .filter(SubmissionModel.user_id == user_id)
            .order_by(SubmissionModel.created_at.desc())
            .all()
        )

        results = []
        for sub in submissions:
            # File info
            sub_file = (
                self.session.query(SubmissionFileModel)
                .filter(SubmissionFileModel.submission_id == sub.id)
                .first()
            )
            # Round & Contest info
            round_obj = (
                self.session.query(RoundModel)
                .filter(RoundModel.id == sub.round_id)
                .first()
            )
            contest_obj = None
            if round_obj:
                contest_obj = (
                    self.session.query(ContestModel)
                    .filter(ContestModel.id == round_obj.contest_id)
                    .first()
                )

            # AI Flag
            ai_flag = (
                self.session.query(AIFlagModel)
                .filter(AIFlagModel.submission_id == sub.id)
                .first()
            )

            results.append({
                "id": sub.id,
                "title": sub.title,
                "story_description": sub.story_description,
                "status": sub.status,
                "final_score": float(sub.final_score) if sub.final_score is not None else None,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "updated_at": sub.updated_at.isoformat() if sub.updated_at else None,
                "round_id": sub.round_id,
                "round_title": round_obj.title if round_obj else f"Round #{sub.round_id}",
                "round_number": round_obj.round_number if round_obj else 1,
                "contest_id": contest_obj.id if contest_obj else (round_obj.contest_id if round_obj else None),
                "contest_title": contest_obj.title if contest_obj else "Analog Photography Contest",
                "thumbnail_url": sub_file.thumbnail_url if sub_file else None,
                "image_hd_url": sub_file.image_hd_url if sub_file else None,
                "ai_flag": {
                    "confidence_score": float(ai_flag.confidence_score) if ai_flag and ai_flag.confidence_score is not None else None,
                    "risk_level": ai_flag.risk_level if ai_flag else "safe",
                    "status": ai_flag.status if ai_flag else "pending",
                } if ai_flag else None,
            })

        return results

    def get_submission_full_details(self, submission_id: int) -> Optional[dict]:
        """Fetch complete submission details including file, film metadata, contest, round, AI flags, scores, and feedbacks."""
        submission = (
            self.session.query(SubmissionModel)
            .filter(SubmissionModel.id == submission_id)
            .first()
        )
        if not submission:
            return None

        # File info
        sub_file = (
            self.session.query(SubmissionFileModel)
            .filter(SubmissionFileModel.submission_id == submission_id)
            .first()
        )

        # Film metadata
        film_metadata = (
            self.session.query(SubmissionFilmMetadataModel)
            .filter(SubmissionFilmMetadataModel.submission_id == submission_id)
            .first()
        )

        # Round & Contest
        round_obj = (
            self.session.query(RoundModel)
            .filter(RoundModel.id == submission.round_id)
            .first()
        )
        contest_obj = None
        if round_obj:
            contest_obj = (
                self.session.query(ContestModel)
                .filter(ContestModel.id == round_obj.contest_id)
                .first()
            )

        # AI flag & Report
        ai_flag = (
            self.session.query(AIFlagModel)
            .filter(AIFlagModel.submission_id == submission_id)
            .first()
        )
        ai_report = (
            self.session.query(AIAnalysisReportModel)
            .filter(AIAnalysisReportModel.submission_id == submission_id)
            .first()
        )

        # Scores breakdown with criteria
        scores_query = (
            self.session.query(ScoreModel, CriteriaModel)
            .outerjoin(CriteriaModel, ScoreModel.criteria_id == CriteriaModel.id)
            .filter(ScoreModel.submission_id == submission_id)
            .all()
        )
        scores_list = []
        for score, criteria in scores_query:
            scores_list.append({
                "id": score.id,
                "judge_id": score.judge_id,
                "criteria_id": score.criteria_id,
                "criteria_name": criteria.name if criteria else f"Criteria #{score.criteria_id}",
                "max_score": float(criteria.max_score) if criteria and criteria.max_score else 100.0,
                "weight": float(criteria.weight) if criteria and criteria.weight else 1.0,
                "score_value": float(score.score_value) if score.score_value is not None else 0.0,
                "comment": score.comment or "",
                "created_at": score.created_at.isoformat() if score.created_at else None,
            })

        # Score feedbacks
        feedbacks_query = (
            self.session.query(ScoreFeedbackModel)
            .filter(ScoreFeedbackModel.submission_id == submission_id)
            .all()
        )
        feedbacks_list = []
        for fb in feedbacks_query:
            feedbacks_list.append({
                "id": fb.id,
                "judge_id": fb.judge_id,
                "summary_feedback": fb.summary_feedback,
                "general_comment": fb.general_comment or "",
                "final_recommendation": fb.final_recommendation or "",
                "is_finalized": fb.is_finalized,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            })

        return {
            "id": submission.id,
            "user_id": submission.user_id,
            "round_id": submission.round_id,
            "title": submission.title,
            "story_description": submission.story_description or "",
            "status": submission.status,
            "final_score": float(submission.final_score) if submission.final_score is not None else None,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "created_at": submission.created_at.isoformat() if submission.created_at else None,
            "updated_at": submission.updated_at.isoformat() if submission.updated_at else None,
            "contest": {
                "id": contest_obj.id if contest_obj else None,
                "title": contest_obj.title if contest_obj else "Analog Photography Contest",
                "slug": contest_obj.slug if contest_obj else "",
                "description": contest_obj.description if contest_obj else "",
            } if contest_obj else None,
            "round": {
                "id": round_obj.id if round_obj else submission.round_id,
                "title": round_obj.title if round_obj else f"Round #{submission.round_id}",
                "round_number": round_obj.round_number if round_obj else 1,
            } if round_obj else None,
            "file": {
                "id": sub_file.id,
                "image_hd_url": sub_file.image_hd_url,
                "thumbnail_url": sub_file.thumbnail_url or sub_file.image_hd_url,
                "file_size_bytes": sub_file.file_size_bytes,
                "width_px": sub_file.width_px,
                "height_px": sub_file.height_px,
                "file_hash": sub_file.file_hash,
                "created_at": sub_file.created_at.isoformat() if sub_file.created_at else None,
            } if sub_file else None,
            "film_metadata": {
                "film_stock": film_metadata.film_stock,
                "film_iso": film_metadata.film_iso,
                "camera_body": film_metadata.camera_body or "",
                "lens": film_metadata.lens or "",
                "lab_name": film_metadata.lab_name or "",
                "scanner_info": film_metadata.scanner_info or "",
                "development_process": film_metadata.development_process or "C-41",
                "taken_at_location": film_metadata.taken_at_location or "",
                "created_at": film_metadata.created_at.isoformat() if film_metadata and film_metadata.created_at else None,
            } if film_metadata else None,
            "ai_flag": {
                "id": ai_flag.id,
                "confidence_score": float(ai_flag.confidence_score) if ai_flag.confidence_score is not None else 0.0,
                "risk_level": ai_flag.risk_level,
                "flag_type": ai_flag.flag_type,
                "status": ai_flag.status,
            } if ai_flag else None,
            "ai_report": {
                "id": ai_report.id,
                "ai_model_name": ai_report.ai_model_name,
                "ai_confidence_score": float(ai_report.ai_confidence_score) if ai_report.ai_confidence_score is not None else 0.0,
                "raw_details": ai_report.raw_details or {},
            } if ai_report else None,
            "scores": scores_list,
            "feedbacks": feedbacks_list,
        }

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
    ) -> SubmissionModel:
        """Update an existing submission in draft state."""
        try:
            submission = (
                self.session.query(SubmissionModel)
                .filter(SubmissionModel.id == submission_id)
                .first()
            )
            if not submission:
                raise ValueError("Submission not found")

            if submission.user_id != user_id:
                raise PermissionError("You can only edit your own submission")

            if submission.status != "draft":
                raise ValueError(f"Cannot edit submission with status '{submission.status}'. Only drafts can be modified.")

            if title:
                submission.title = title
            if story_description is not None:
                submission.story_description = story_description
            if round_id:
                submission.round_id = round_id
            if status:
                submission.status = status
                if status == "submitted":
                    from datetime import datetime, timezone
                    submission.submitted_at = datetime.now(timezone.utc)

            # Update or create Film Metadata
            if film_metadata is not None:
                meta = (
                    self.session.query(SubmissionFilmMetadataModel)
                    .filter(SubmissionFilmMetadataModel.submission_id == submission_id)
                    .first()
                )
                if meta:
                    if "film_stock" in film_metadata and film_metadata["film_stock"]:
                        meta.film_stock = film_metadata["film_stock"]
                    if "film_iso" in film_metadata:
                        meta.film_iso = int(film_metadata["film_iso"]) if film_metadata["film_iso"] else None
                    if "camera_body" in film_metadata:
                        meta.camera_body = film_metadata["camera_body"]
                    if "lens" in film_metadata:
                        meta.lens = film_metadata["lens"]
                    if "lab_name" in film_metadata:
                        meta.lab_name = film_metadata["lab_name"]
                    if "scanner_info" in film_metadata:
                        meta.scanner_info = film_metadata["scanner_info"]
                    if "development_process" in film_metadata:
                        meta.development_process = film_metadata["development_process"] or "C-41"
                    if "taken_at_location" in film_metadata:
                        meta.taken_at_location = film_metadata["taken_at_location"]
                else:
                    new_meta = SubmissionFilmMetadataModel(
                        submission_id=submission_id,
                        film_stock=film_metadata.get("film_stock", ""),
                        film_iso=int(film_metadata["film_iso"]) if film_metadata.get("film_iso") else None,
                        camera_body=film_metadata.get("camera_body"),
                        lens=film_metadata.get("lens"),
                        lab_name=film_metadata.get("lab_name"),
                        scanner_info=film_metadata.get("scanner_info"),
                        development_process=film_metadata.get("development_process", "C-41"),
                        taken_at_location=film_metadata.get("taken_at_location"),
                    )
                    self.session.add(new_meta)

            # Update File if new image provided
            if image_hd_url and file_hash:
                sub_file = (
                    self.session.query(SubmissionFileModel)
                    .filter(SubmissionFileModel.submission_id == submission_id)
                    .first()
                )
                if sub_file:
                    sub_file.image_hd_url = image_hd_url
                    sub_file.file_hash = file_hash
                    if thumbnail_url:
                        sub_file.thumbnail_url = thumbnail_url
                    if width_px:
                        sub_file.width_px = width_px
                    if height_px:
                        sub_file.height_px = height_px
                    if file_size_bytes:
                        sub_file.file_size_bytes = file_size_bytes
                else:
                    new_file = SubmissionFileModel(
                        submission_id=submission_id,
                        image_hd_url=image_hd_url,
                        thumbnail_url=thumbnail_url,
                        file_hash=file_hash,
                        width_px=width_px,
                        height_px=height_px,
                        file_size_bytes=file_size_bytes,
                    )
                    self.session.add(new_file)

            self.session.commit()
            self.session.refresh(submission)
            return submission
        except Exception:
            self.session.rollback()
            raise