"""Submission review ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class SubmissionReviewModel(Base):
    __tablename__ = "submission_reviews"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_status = Column(String(20), nullable=False, default="pending")
    review_notes = Column(Text, nullable=True)
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
