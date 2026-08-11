from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class AIAnalysisReportModel(Base):
    __tablename__ = 'ai_analysis_reports'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False)
    ai_flag_id = Column(BigInteger, ForeignKey('ai_flags.id', ondelete='SET NULL'), nullable=True)
    model_version = Column(String(50), nullable=False)
    analysis_details = Column(JSON, nullable=True)
    raw_response_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
