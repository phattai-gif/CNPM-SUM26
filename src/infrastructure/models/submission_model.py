from sqlalchemy import Column, Integer, String, DateTime

from infrastructure.databases.base import Base


class SubmissionModel(Base):
    __tablename__ = 'submissions'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    contest_id = Column(Integer, nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default='pending')
    file_url = Column(String(255), nullable=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
