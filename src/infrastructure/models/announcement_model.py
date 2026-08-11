from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class ContestAnnouncementModel(Base):
    __tablename__ = 'contest_announcements'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contest_id = Column(BigInteger, ForeignKey('contests.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_by = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
