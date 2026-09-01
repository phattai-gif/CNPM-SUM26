"""Repository for Vote model operations."""

from typing import Optional, List
from sqlalchemy.orm import Session

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import VoteModel


class VoteRepository:
    def __init__(self, session: Optional[Session] = None):
        if session is not None:
            self.session = session
        else:
            self.session = db_factory.get_database('POSTGREE').session

    def create_vote(self, user_id: int, submission_id: int) -> VoteModel:
        """Create a new vote (will fail if unique constraint violated)."""
        vote = VoteModel(
            user_id=user_id,
            submission_id=submission_id,
        )
        self.session.add(vote)
        self.session.commit()
        self.session.refresh(vote)
        return vote

    def get_vote(self, user_id: int, submission_id: int) -> Optional[VoteModel]:
        """Get a vote by user and submission."""
        return self.session.query(VoteModel).filter_by(
            user_id=user_id,
            submission_id=submission_id
        ).first()

    def has_voted(self, user_id: int, submission_id: int) -> bool:
        """Check if user has already voted on submission."""
        return self.session.query(VoteModel).filter_by(
            user_id=user_id,
            submission_id=submission_id
        ).first() is not None

    def delete_vote(self, user_id: int, submission_id: int) -> bool:
        """Delete a vote. Returns True if found and deleted, False if not found."""
        vote = self.session.query(VoteModel).filter_by(
            user_id=user_id,
            submission_id=submission_id
        ).first()
        if vote is None:
            return False
        self.session.delete(vote)
        self.session.commit()
        return True

    def get_vote_count(self, submission_id: int) -> int:
        """Get total number of votes for a submission."""
        return self.session.query(VoteModel).filter_by(
            submission_id=submission_id
        ).count()

    def list_votes_by_submission(self, submission_id: int) -> List[VoteModel]:
        """Get all votes for a submission."""
        return self.session.query(VoteModel).filter_by(
            submission_id=submission_id
        ).order_by(VoteModel.created_at.desc()).all()

    def list_votes_by_user(self, user_id: int) -> List[VoteModel]:
        """Get all votes cast by a user."""
        return self.session.query(VoteModel).filter_by(
            user_id=user_id
        ).order_by(VoteModel.created_at.desc()).all()
