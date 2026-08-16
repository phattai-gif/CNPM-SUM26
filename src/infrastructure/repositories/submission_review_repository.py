from typing import Optional, List
from sqlalchemy.orm import Session

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import SubmissionReviewModel


class SubmissionReviewRepository:
    def __init__(self, session: Optional[Session] = None):
        if session is not None:
            self.session = session
        else:
            self.session = db_factory.get_database('POSTGREE').session

    def create(self, submission_id: int, reviewer_id: Optional[int] = None,
               review_status: str = 'pending', review_notes: Optional[str] = None,
               decision_reason: Optional[str] = None) -> SubmissionReviewModel:
        model = SubmissionReviewModel(
            submission_id=submission_id,
            reviewer_id=reviewer_id,
            review_status=review_status,
            review_notes=review_notes,
            decision_reason=decision_reason,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model

    def get_by_submission(self, submission_id: int) -> Optional[SubmissionReviewModel]:
        return self.session.query(SubmissionReviewModel).filter_by(submission_id=submission_id).first()

    def list_by_submission(self, submission_id: int) -> List[SubmissionReviewModel]:
        return self.session.query(SubmissionReviewModel).filter_by(submission_id=submission_id).all()

    def update_status(self, review_id: int, review_status: str, review_notes: Optional[str] = None,
                      decision_reason: Optional[str] = None) -> Optional[SubmissionReviewModel]:
        model = self.session.query(SubmissionReviewModel).filter_by(id=review_id).first()
        if model is None:
            return None
        model.review_status = review_status
        if review_notes is not None:
            model.review_notes = review_notes
        if decision_reason is not None:
            model.decision_reason = decision_reason
        self.session.commit()
        self.session.refresh(model)
        return model
