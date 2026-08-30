"""Service for vote operations on submissions."""

from typing import Optional, Tuple

from infrastructure.repositories.vote_repository import VoteRepository
from infrastructure.repositories.submission_repository import SubmissionRepository


class VoteService:
    def __init__(
        self,
        vote_repo: Optional[VoteRepository] = None,
        submission_repo: Optional[SubmissionRepository] = None,
    ):
        self.vote_repo = vote_repo or VoteRepository()
        self.submission_repo = submission_repo or SubmissionRepository()

    def vote_submission(
        self,
        user_id: int,
        submission_id: int,
    ) -> Tuple[dict, Optional[str]]:
        """
        User votes on a submission.
        
        Returns:
            (vote_dict, error)
            - If successful: (vote dict with vote_id and timestamp, None)
            - If error: (None, error_code)
        
        Error codes:
            - "submission_not_found": submission doesn't exist
            - "submission_not_public": submission is not a winner (not public)
            - "already_voted": user has already voted on this submission
            - "database_error": unexpected database error
        """
        # Check if submission exists and is public (winner status)
        submission = self.submission_repo.get_by_id(submission_id)
        if submission is None:
            return None, "submission_not_found"

        if submission.status != "winner":
            return None, "submission_not_public"

        # Check if user has already voted
        if self.vote_repo.has_voted(user_id, submission_id):
            return None, "already_voted"

        try:
            vote = self.vote_repo.create_vote(user_id, submission_id)
            return {
                "vote_id": vote.id,
                "user_id": vote.user_id,
                "submission_id": vote.submission_id,
                "created_at": vote.created_at.isoformat() if vote.created_at else None,
            }, None
        except Exception as e:
            return None, "database_error"

    def unvote_submission(
        self,
        user_id: int,
        submission_id: int,
    ) -> Tuple[bool, Optional[str]]:
        """
        User removes their vote from a submission.
        
        Returns:
            (success, error)
            - If successful: (True, None)
            - If error: (False, error_code)
        
        Error codes:
            - "vote_not_found": user hasn't voted on this submission
            - "database_error": unexpected database error
        """
        try:
            deleted = self.vote_repo.delete_vote(user_id, submission_id)
            if not deleted:
                return False, "vote_not_found"
            return True, None
        except Exception as e:
            return False, "database_error"

    def get_submission_vote_count(
        self,
        submission_id: int,
    ) -> int:
        """Get total number of votes for a submission."""
        return self.vote_repo.get_vote_count(submission_id)

    def has_user_voted(
        self,
        user_id: int,
        submission_id: int,
    ) -> bool:
        """Check if user has voted on submission."""
        return self.vote_repo.has_voted(user_id, submission_id)

    def get_user_votes(self, user_id: int) -> list:
        """Get list of submission IDs user has voted on."""
        votes = self.vote_repo.list_votes_by_user(user_id)
        return [
            {
                "vote_id": v.id,
                "submission_id": v.submission_id,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in votes
        ]
