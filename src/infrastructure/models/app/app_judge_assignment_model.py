"""Judge assignment ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class JudgeAssignmentModel(Base):
    __tablename__ = "judge_assignments"
    __table_args__ = (
        UniqueConstraint("submission_id", "judge_id", name="unique_judge_submission_assignment"),
        {"schema": "app", "extend_existing": True},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    round_id = Column(BigInteger, ForeignKey("app.rounds.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(BigInteger, ForeignKey("app.submissions.id", ondelete="CASCADE"), nullable=True)
    judge_id = Column(BigInteger, ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="assigned")
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
