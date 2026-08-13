from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from domain.models.isubmission_repository import ISubmissionRepository
from domain.models.submission import Submission
from infrastructure.databases.factory_database import (
    FactoryDatabase as db_factory
)
from infrastructure.models.submission_model import SubmissionModel
from infrastructure.models.submission_file_model import (
    SubmissionFileModel
)
from infrastructure.models.film_metadata_model import (
    SubmissionFilmMetadataModel
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