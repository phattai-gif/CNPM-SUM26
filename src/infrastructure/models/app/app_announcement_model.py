"""Contest announcement ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class ContestAnnouncementModel(Base):
    __tablename__ = "contest_announcements"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contest_id = Column(BigInteger, ForeignKey("app.contests.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(BigInteger, ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    contest = relationship("ContestModel", foreign_keys="ContestAnnouncementModel.contest_id")
    creator = relationship("UserModel", foreign_keys="ContestAnnouncementModel.created_by")
