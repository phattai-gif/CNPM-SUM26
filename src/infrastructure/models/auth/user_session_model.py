from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class UserSessionModel(Base):
    __tablename__ = 'user_sessions'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    refresh_token = Column(String(512), nullable=False, unique=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
