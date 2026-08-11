from sqlalchemy import Column, BigInteger, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class DigitalArchiveExhibitModel(Base):
    """
    Bảng lưu bài thi xuất sắc / đạt giải phục vụ Triển lãm Trực tuyến lâu dài (Digital Archive)
    """
    __tablename__ = 'digital_archive_exhibits'
    __table_args__ = (
        UniqueConstraint('contest_id', 'submission_id', name='unique_exhibit_submission'),
        {'extend_existing': True}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contest_id = Column(BigInteger, ForeignKey('contests.id', ondelete='CASCADE'), nullable=False)
    submission_id = Column(BigInteger, ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False)
    award_title = Column(String(100), nullable=True) # Vd: Giải Nhất, Best Film Color
    display_order = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    published_at = Column(DateTime(timezone=True), server_default=func.now())
