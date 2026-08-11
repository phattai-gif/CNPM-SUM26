from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class TeamInvitationModel(Base):
    __tablename__ = 'team_invitations'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    team_id = Column(BigInteger, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
