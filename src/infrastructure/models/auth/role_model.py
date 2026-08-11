from sqlalchemy import Column, BigInteger, String, ForeignKey, Table
from infrastructure.databases.base import Base

# Bảng trung gian User-Role
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', BigInteger, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', BigInteger, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)

# Bảng trung gian Role-Permission
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', BigInteger, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', BigInteger, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

class RoleModel(Base):
    __tablename__ = 'roles'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)

class PermissionModel(Base):
    __tablename__ = 'permissions'
    __table_args__ = {'extend_existing': True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    module = Column(String(50), nullable=False)
