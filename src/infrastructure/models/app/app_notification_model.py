"""Notification ORM model."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class NotificationModel(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contest_id = Column(BigInteger, ForeignKey("contests.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    notification_type = Column(String(50), nullable=False, default="info")
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
