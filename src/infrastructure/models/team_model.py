from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class TeamModel(Base):
    __tablename__ = 'teams'
    __table_args__ = (
        UniqueConstraint('contest_id', 'name', name='unique_contest_team_name'),
        {'extend_existing': True}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contest_id = Column(BigInteger, ForeignKey('contests.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    leader_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    invite_code = Column(String(20), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
