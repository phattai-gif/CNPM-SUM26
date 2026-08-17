"""Contest settings ORM model."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class ContestSettingsModel(Base):
    __tablename__ = "contest_settings"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contest_id = Column(BigInteger, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False, unique=True)
    allow_public_vote = Column(Boolean, nullable=False, default=False)
    allow_submission = Column(Boolean, nullable=False, default=True)
    max_submission_per_user = Column(Integer, nullable=False, default=1)
    scoring_mode = Column(String(50), nullable=False, default="weighted")
    judges_visible = Column(Boolean, nullable=False, default=False)
    announcement_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
