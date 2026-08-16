"""Submission film metadata ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class SubmissionFilmMetadataModel(Base):
    __tablename__ = "submission_film_metadata"
    __table_args__ = {"schema": "app", "extend_existing": True}

    submission_id = Column(BigInteger, ForeignKey("submissions.id", ondelete="CASCADE"), primary_key=True)
    film_stock = Column(String(100), nullable=False)
    film_iso = Column(Integer, nullable=True)
    camera_body = Column(String(100), nullable=True)
    lens = Column(String(100), nullable=True)
    lab_name = Column(String(150), nullable=True)
    scanner_info = Column(String(150), nullable=True)
    development_process = Column(String(50), default="C-41")
    taken_at_location = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
