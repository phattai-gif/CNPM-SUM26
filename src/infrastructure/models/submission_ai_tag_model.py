from sqlalchemy import Column, BigInteger, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class SubmissionAITagModel(Base):
    """
    Bảng lưu vết Keywords / Tags tự động sinh từ Module AI cho bài thi ảnh phim
    (Ví dụ: Street, Portrait, Monochrome, Urban, Landscape)
    """
    __tablename__ = 'submission_ai_tags'
    __table_args__ = (
        UniqueConstraint('submission_id', 'tag_name', name='unique_submission_tag'),
        {'extend_existing': True}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False)
    tag_name = Column(String(50), nullable=False)
    confidence = Column(Numeric(5, 2), default=90.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
