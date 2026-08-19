"""Submission ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class SubmissionModel(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("round_id", "user_id", "title", name="unique_user_round_photo"),
        {"schema": "app", "extend_existing": True},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    round_id = Column(BigInteger, ForeignKey("app.rounds.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    story_description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="submitted")
    final_score = Column(Numeric(5, 2), nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    round = relationship("RoundModel", back_populates="submissions")
    user = relationship("UserModel", back_populates="submissions")
    files = relationship("SubmissionFileModel", back_populates="submission", cascade="all, delete-orphan")
    film_metadata = relationship("SubmissionFilmMetadataModel", back_populates="submission", uselist=False, cascade="all, delete-orphan")
    scores = relationship("ScoreModel", back_populates="submission", cascade="all, delete-orphan")
    ai_flags = relationship("AIFlagModel", back_populates="submission", cascade="all, delete-orphan")
