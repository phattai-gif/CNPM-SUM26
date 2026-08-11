from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from infrastructure.databases.base import Base

class AuditLogModel(Base):
    __tablename__ = 'audit_logs'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(100), nullable=False)
    entity_name = Column(String(50), nullable=False)
    entity_id = Column(BigInteger, nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
