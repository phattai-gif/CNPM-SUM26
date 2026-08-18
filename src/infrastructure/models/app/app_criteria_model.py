"""Criteria ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class CriteriaModel(Base):
    __tablename__ = "criteria"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    round_id = Column(BigInteger, ForeignKey("app.rounds.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_score = Column(Numeric(5, 2), nullable=False, default=10.00)
    weight = Column(Numeric(5, 2), nullable=False, default=1.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # updated_at removed: some DB deployments lack this column and cause UndefinedColumn errors
