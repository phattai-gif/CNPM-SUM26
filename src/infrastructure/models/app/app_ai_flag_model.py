"""AI flag ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class AIFlagModel(Base):
    __tablename__ = "ai_flags"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey("app.submissions.id", ondelete="CASCADE"), nullable=False)
    flag_type = Column(String(50), nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=False)
    risk_level = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="pending")
    reviewed_by = Column(BigInteger, ForeignKey("app.users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    submission = relationship("SubmissionModel", back_populates="ai_flags")
    analysis_report = relationship("AIAnalysisReportModel", back_populates="ai_flag", uselist=False, cascade="all, delete-orphan")
    reviewed_by_user = relationship("UserModel", back_populates="reviewed_ai_flags", foreign_keys="AIFlagModel.reviewed_by")
