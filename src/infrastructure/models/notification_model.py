from sqlalchemy import Column, BigInteger, String, Text, DateTime
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class NotificationModel(Base):
    __tablename__ = 'notifications'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(50), nullable=False, default='system')
    target_link = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
