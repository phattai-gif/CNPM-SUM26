from sqlalchemy import delete, insert, select

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import RoleModel, UserModel, user_roles


class AdminUserRepository:
    def __init__(self, session=None):
        self.session = session or db_factory.get_database('POSTGREE').session

    def _role_code_subquery(self):
        return (
            select(RoleModel.code)
            .select_from(user_roles)
            .join(RoleModel, user_roles.c.role_id == RoleModel.id)
            .where(user_roles.c.user_id == UserModel.id)
            .limit(1)
            .scalar_subquery()
        )

    @staticmethod
    def serialize(user, role_code):
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': role_code or 'participant',
            'status': user.status,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }

    def list_users(self, page=1, per_page=20, search=None, role=None, status=None):
        role_code = self._role_code_subquery()
        query = self.session.query(UserModel, role_code.label('role_code'))
        if search:
            pattern = f'%{search}%'
            query = query.filter(
                UserModel.username.ilike(pattern) |
                UserModel.email.ilike(pattern) |
                UserModel.full_name.ilike(pattern)
            )
        if status:
            query = query.filter(UserModel.status == status)
        if role:
            query = query.filter(role_code == role)

        total = query.count()
        rows = (
            query.order_by(UserModel.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return [self.serialize(user, code) for user, code in rows], total

    def get_user(self, user_id):
        role_code = self._role_code_subquery()
        row = (
            self.session.query(UserModel, role_code.label('role_code'))
            .filter(UserModel.id == user_id)
            .first()
        )
        return self.serialize(*row) if row else None

    def get_current_role(self, user_id):
        return self.session.execute(
            select(RoleModel.code)
            .select_from(user_roles)
            .join(RoleModel, user_roles.c.role_id == RoleModel.id)
            .where(user_roles.c.user_id == user_id)
        ).scalar()

    def set_role(self, user_id, role_code):
        role = self.session.query(RoleModel).filter_by(code=role_code).first()
        user = self.session.query(UserModel).filter_by(id=user_id).first()
        if not user or not role:
            return None
        try:
            self.session.execute(delete(user_roles).where(user_roles.c.user_id == user_id))
            self.session.execute(insert(user_roles).values(user_id=user_id, role_id=role.id))
            self.session.commit()
            return self.get_user(user_id)
        except Exception:
            self.session.rollback()
            raise

    def set_status(self, user_id, status):
        user = self.session.query(UserModel).filter_by(id=user_id).first()
        if not user:
            return None
        try:
            user.status = status
            self.session.commit()
            return self.get_user(user_id)
        except Exception:
            self.session.rollback()
            raise