"""User ORM model."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class UserModel(Base):
    """System user model."""

    __tablename__ = "users"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    bio = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    email_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    contests = relationship("ContestModel", back_populates="creator", foreign_keys="ContestModel.created_by")
    submissions = relationship("SubmissionModel", back_populates="user", foreign_keys="SubmissionModel.user_id")
    submitted_scores = relationship("ScoreModel", back_populates="judge", foreign_keys="ScoreModel.judge_id")
    reviewed_ai_flags = relationship("AIFlagModel", back_populates="reviewed_by_user", foreign_keys="AIFlagModel.reviewed_by")
