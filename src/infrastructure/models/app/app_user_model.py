"""User ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, String, Text
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class UserModel(Base):
    """System user model."""

    __tablename__ = "users"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    bio = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
>>>>>>> 790426c04c0df979b2e2951e003243881e743d3d:src/infrastructure/models/user_model.py
