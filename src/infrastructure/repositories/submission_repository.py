from typing import List, Optional

from sqlalchemy.orm import Session

from domain.models.isubmission_repository import ISubmissionRepository
from domain.models.submission import Submission
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.submission_model import SubmissionModel


class SubmissionRepository(ISubmissionRepository):

    def __init__(self, session: Optional[Session] = None):
        self.session = session or db_factory.get_database("POSTGREE").session

    def add(self, submission: Submission) -> SubmissionModel:
        try:
            model = SubmissionModel(
                user_id=submission.user_id,
                contest_id=submission.contest_id,
                title=submission.title,
                description=submission.description,
                status=submission.status,
                file_url=submission.file_url,
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

            model.user_id = submission.user_id
            model.contest_id = submission.contest_id
            model.title = submission.title
            model.description = submission.description
            model.status = submission.status
            model.file_url = submission.file_url
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