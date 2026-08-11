from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class TeamMemberModel(Base):
    __tablename__ = 'team_members'
    __table_args__ = (
        UniqueConstraint('team_id', 'user_id', name='unique_team_user'),
        {'extend_existing': True}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    team_id = Column(BigInteger, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_in_team = Column(String(20), nullable=False, default='member')
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
