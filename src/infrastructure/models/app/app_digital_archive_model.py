"""Digital archive exhibit ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class DigitalArchiveExhibitModel(Base):
    __tablename__ = "digital_archive_exhibits"
    __table_args__ = (
        UniqueConstraint("contest_id", "submission_id", name="unique_exhibit_submission"),
        {"schema": "app", "extend_existing": True},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contest_id = Column(BigInteger, ForeignKey("app.contests.id", ondelete="CASCADE"), nullable=False)
    submission_id = Column(BigInteger, ForeignKey("app.submissions.id", ondelete="CASCADE"), nullable=False)
    award_title = Column(String(100), nullable=True)
    display_order = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    published_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
