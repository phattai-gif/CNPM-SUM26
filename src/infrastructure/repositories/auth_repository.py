from typing import Optional

from sqlalchemy import insert, select
from werkzeug.security import check_password_hash

from domain.models.iauth_repository import IAuthRepository
from domain.models.auth import Auth
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import UserModel, RoleModel, user_roles


class AuthRepository(IAuthRepository):
    def __init__(self, session=None):
        if session is not None:
            self.session = session
        else:
            self.session = db_factory.get_database('POSTGREE').session

    def check_exist(self, username: str) -> bool:
        existing_user = self.session.query(UserModel).filter_by(username=username).first()
        return existing_user is not None

    def check_email_exist(self, email: str) -> bool:
        existing_user = self.session.query(UserModel).filter_by(email=email).first()
        return existing_user is not None

    def register(self, auth: Auth) -> Optional[Auth]:
        try:
            # 1. Táº¡o user má»›i trong báº£ng users
            new_user = UserModel(
                username=auth.username,
                email=auth.email,
                password_hash=auth.password,
                full_name=auth.full_name,
                status='active'
            )
            self.session.add(new_user)
            self.session.flush()  # Láº¥y id má»›i sinh

            # 2. TÃ¬m role_id tÆ°Æ¡ng á»©ng vá»›i role code (máº·c Ä‘á»‹nh: 'participant')
            role_code = auth.role if auth.role else 'participant'
            role_obj = self.session.query(RoleModel).filter_by(code=role_code).first()

            if role_obj is None:
                role_obj = RoleModel(
                    code=role_code,
                    name=role_code.replace('_', ' ').title(),
                    description=f'Default {role_code} role',
                )
                self.session.add(role_obj)
                self.session.flush()

            stmt = insert(user_roles).values(user_id=new_user.id, role_id=role_obj.id)
            self.session.execute(stmt)

            self.session.commit()
            auth.id = new_user.id
            return auth
        except Exception as e:
            self.session.rollback()
            print(f"Error registering user: {e}")
            return None

    def login(self, auth: Auth) -> Optional[Auth]:
        try:
            # TÃ¬m user theo username
            user_obj = self.session.query(UserModel).filter_by(username=auth.username).first()
            if not user_obj:
                return None

            # Kiá»ƒm tra máº­t kháº©u mÃ£ hÃ³a vá»›i check_password_hash
            if not check_password_hash(user_obj.password_hash, auth.password):
                return None

            # Láº¥y role code cá»§a user
            role_code = self.get_user_role(user_obj.id) or 'participant'

            auth.id = user_obj.id
            auth.email = user_obj.email
            auth.full_name = user_obj.full_name
            auth.role = role_code
            return auth
        except Exception as e:
            print(f"Error logging in: {e}")
            return None

    def get_user_role(self, user_id: int) -> Optional[str]:
        try:
            stmt = (
                select(RoleModel.code)
                .select_from(user_roles)
                .join(RoleModel, user_roles.c.role_id == RoleModel.id)
                .where(user_roles.c.user_id == user_id)
            )
            result = self.session.execute(stmt).scalar()
            return result
        except Exception as e:
            print(f"Error fetching user role: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Auth]:
        try:
            user_obj = self.session.query(UserModel).filter_by(id=user_id).first()
            if not user_obj:
                return None

            role_code = self.get_user_role(user_id) or 'participant'
            return Auth(
                id=user_obj.id,
                username=user_obj.username,
                password='',
                passwordcomfirm='',
                email=user_obj.email,
                role=role_code,
                full_name=user_obj.full_name
            )
        except Exception as e:
            print(f"Error fetching user by id: {e}")
            return None

