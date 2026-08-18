"""AI flag ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class AIFlagModel(Base):
    __tablename__ = "ai_flags"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    flag_type = Column(String(50), nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
