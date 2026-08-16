"""Submission file ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class SubmissionFileModel(Base):
    __tablename__ = "submission_files"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    submission_id = Column(BigInteger, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    image_hd_url = Column(String(512), nullable=False)
    thumbnail_url = Column(String(512), nullable=True)
    width_px = Column(Integer, nullable=True)
    height_px = Column(Integer, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    file_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
