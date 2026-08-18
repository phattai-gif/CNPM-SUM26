"""Submission AI tag ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class SubmissionAITagModel(Base):
    __tablename__ = "submission_ai_tags"
    __table_args__ = (
        UniqueConstraint("submission_id", "tag_name", name="unique_submission_tag"),
        {"schema": "app", "extend_existing": True},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey("app.submissions.id", ondelete="CASCADE"), nullable=False)
    tag_name = Column(String(50), nullable=False)
    confidence = Column(Numeric(5, 2), default=90.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
