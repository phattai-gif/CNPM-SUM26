"""Role and permission ORM models."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class RoleModel(Base):
    """Role model."""

    __tablename__ = "roles"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    # created_at column removed to match existing DB schema (some DBs lack this column)


class PermissionModel(Base):
    """Permission model."""

    __tablename__ = "permissions"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    module = Column(String(50), nullable=False)
    # created_at column removed to match existing DB schema (some DBs lack this column)


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("app.users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", BigInteger, ForeignKey("app.roles.id", ondelete="CASCADE"), primary_key=True),
    schema="app",
    extend_existing=True,
)


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", BigInteger, ForeignKey("app.roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("app.permissions.id", ondelete="CASCADE"), primary_key=True),
    schema="app",
    extend_existing=True,
)
