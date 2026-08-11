from typing import List, Optional

from sqlalchemy.orm import Session

from domain.models.isubmission_repository import ISubmissionRepository
from domain.models.submission import Submission
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.submission_model import SubmissionModel
from infrastructure.models.submission_file_model import SubmissionFileModel
from infrastructure.models.film_metadata_model import SubmissionFilmMetadataModel


class SubmissionRepository(ISubmissionRepository):

    def __init__(self, session: Optional[Session] = None):
        self.session = session or db_factory.get_database("POSTGREE").session

    def add(self, submission: Submission) -> SubmissionModel:
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

    def create_submission(
        self,
        round_id: int,
        user_id: int,
        title: str,
        image_hd_url: str,
        story_description: str = "",
        thumbnail_url: Optional[str] = None,
        width_px: Optional[int] = None,
        height_px: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        file_hash: Optional[str] = None,
        film_stock: Optional[str] = None,
        film_iso: Optional[int] = None,
        camera_body: Optional[str] = None,
        lens: Optional[str] = None,
        lab_name: Optional[str] = None,
        scanner_info: Optional[str] = None,
        development_process: str = "C-41",
        taken_at_location: Optional[str] = None,
        status: str = "submitted",
    ):
        try:
            submission_model = self.add(
                Submission(
                    round_id=round_id,
                    user_id=user_id,
                    title=title,
                    story_description=story_description,
                    status=status,
                )
            )

            submission_file = SubmissionFileModel(
                submission_id=submission_model.id,
                image_hd_url=image_hd_url,
                thumbnail_url=thumbnail_url,
                width_px=width_px,
                height_px=height_px,
                file_size_bytes=file_size_bytes,
                file_hash=file_hash or "",
            )
            self.session.add(submission_file)

            if film_stock:
                metadata = SubmissionFilmMetadataModel(
                    submission_id=submission_model.id,
                    film_stock=film_stock,
                    film_iso=film_iso,
                    camera_body=camera_body,
                    lens=lens,
                    lab_name=lab_name,
                    scanner_info=scanner_info,
                    development_process=development_process,
                    taken_at_location=taken_at_location,
                )
                self.session.add(metadata)

            self.session.commit()
            self.session.refresh(submission_model)
            return submission_model

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

    def list(self) -> List[SubmissionModel]:
        return self.session.query(SubmissionModel).all()

    def update(self, submission: Submission) -> SubmissionModel:
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
            model.story_description = submission.story_description
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

    def delete(self, submission_id: int) -> None:
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