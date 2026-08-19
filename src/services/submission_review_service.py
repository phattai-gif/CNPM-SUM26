from typing import Optional

from infrastructure.repositories.submission_review_repository import SubmissionReviewRepository


class SubmissionReviewService:
    def __init__(self, repository: Optional[SubmissionReviewRepository] = None):
        self.repository = repository or SubmissionReviewRepository()

    def create_review(self, submission_id: int, reviewer_id: Optional[int] = None,
                      review_status: str = 'pending', review_notes: Optional[str] = None,
                      decision_reason: Optional[str] = None):
        return self.repository.create(
            submission_id=submission_id,
            reviewer_id=reviewer_id,
            review_status=review_status,
            review_notes=review_notes,
            decision_reason=decision_reason,
        )

    def get_review_by_submission(self, submission_id: int):
        return self.repository.get_by_submission(submission_id)

    def update_review_status(self, review_id: int, review_status: str,
                            review_notes: Optional[str] = None,
                            decision_reason: Optional[str] = None):
        return self.repository.update_status(
            review_id=review_id,
            review_status=review_status,
            review_notes=review_notes,
            decision_reason=decision_reason,
        )

