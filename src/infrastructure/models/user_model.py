from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class UserModel(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    status = Column(String(20), nullable=False, default='active')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())