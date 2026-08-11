from sqlalchemy import Column, BigInteger, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class UserNotificationModel(Base):
    __tablename__ = 'user_notifications'
    __table_args__ = (
        UniqueConstraint('notification_id', 'user_id', name='unique_user_notification'),
        {'extend_existing': True}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    notification_id = Column(BigInteger, ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
