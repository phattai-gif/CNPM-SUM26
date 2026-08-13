from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class ScoreFeedbackModel(Base):
    __tablename__ = "score_feedbacks"

    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "judge_id",
            name="unique_judge_submission_feedback",
        ),
        {"extend_existing": True},
    )

    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    submission_id = Column(
        BigInteger,
        ForeignKey(
            "submissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    judge_id = Column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    summary_feedback = Column(
        Text,
        nullable=False,
    )

    final_recommendation = Column(
        String(50),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    