"""Vote ORM model for public voting on submissions."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class VoteModel(Base):
    """User vote on a submission (one vote per user per submission)."""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("user_id", "submission_id", name="unique_user_submission_vote"),
        {"schema": "app", "extend_existing": True},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(BigInteger, ForeignKey("app.submissions.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserModel", foreign_keys="VoteModel.user_id")
    submission = relationship("SubmissionModel", foreign_keys="VoteModel.submission_id")
