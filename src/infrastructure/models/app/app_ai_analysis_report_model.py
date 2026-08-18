"""AI analysis report ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, JSON, Numeric, String
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class AIAnalysisReportModel(Base):
    __tablename__ = "ai_analysis_reports"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    ai_flag_id = Column(BigInteger, ForeignKey("ai_flags.id", ondelete="SET NULL"), nullable=True)
    ai_model_name = Column(String(50), nullable=False)
    ai_confidence_score = Column(Numeric(5, 2), nullable=True)
    similarity_matched_submission_id = Column(BigInteger, ForeignKey("submissions.id", ondelete="SET NULL"), nullable=True)
    raw_details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
