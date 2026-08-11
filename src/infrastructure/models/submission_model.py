from sqlalchemy import Column, BigInteger, String, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class SubmissionModel(Base):
    __tablename__ = 'submissions'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    round_id = Column(BigInteger, ForeignKey('rounds.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    story_description = Column(Text, nullable=True) # Lời tự sự / câu chuyện tác phẩm
    status = Column(String(20), nullable=False, default='submitted') # submitted, flagged, approved, evaluated
    final_score = Column(Numeric(5, 2), nullable=True) # Điểm chốt vòng
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
