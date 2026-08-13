from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class ScoreModel(Base):
    __tablename__ = "scores"

    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "judge_id",
            "criteria_id",
            name="unique_judge_submission_criteria",
        ),
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

    criteria_id = Column(
        BigInteger,
        ForeignKey(
            "criteria.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    score_value = Column(
        Numeric(5, 2),
        nullable=False,
    )

    comment = Column(
        Text,
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
    