"""Contest ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class ContestModel(Base):
    __tablename__ = "contests"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    rules = Column(Text, nullable=True)
    banner_url = Column(String(512), nullable=True)
    created_by = Column(BigInteger, ForeignKey("app.users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to the user who created the contest. Table is schema-qualified as 'app.users'.
    creator = relationship("UserModel", primaryjoin="ContestModel.created_by==UserModel.id", foreign_keys=[created_by], uselist=False)
