from typing import Optional
from sqlalchemy import func, insert, select
from secrets import token_urlsafe
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
            # 1. Tạo user mới trong bảng User
            new_user = UserModel(
                username=auth.username,
                email=auth.email,
                password_hash=auth.password,
                full_name=auth.full_name,
                     status='active',
                     email_verified=False
            )
            self.session.add(new_user)
            self.session.flush()  # Lấy ID của user mới

            # 2. Tìm role_id tương ứng với role_code, mặc định là "participant"
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
            # Tìm user theo username
            user_obj = self.session.query(UserModel).filter_by(username=auth.username).first()
            if not user_obj:
                return None

            if user_obj.status != 'active':
                return None

            # Kiểm tra mật khẩu mã hóa với check_password_hash
            if not check_password_hash(user_obj.password_hash, auth.password):
                return None

            # Lấy role code của user
            role_code = self.get_user_role(user_obj.id) or 'participant'

            auth.id = user_obj.id
            auth.email = user_obj.email
            auth.full_name = user_obj.full_name
            auth.role = role_code
            return auth
        except Exception as e:
            print(f"Error logging in: {e}")
            return None

    def login_google(self, email: str, full_name: str = None, avatar_url: str = None) -> Optional[Auth]:
        """Find an active account by verified Google email or create a participant."""
        try:
            user_obj = self.session.query(UserModel).filter(
                func.lower(UserModel.email) == email.lower()
            ).first()
            if user_obj:
                if user_obj.status != 'active':
                    return None
                user_obj.email_verified = True
                if full_name and not user_obj.full_name:
                    user_obj.full_name = full_name
                if avatar_url and not user_obj.avatar_url:
                    user_obj.avatar_url = avatar_url
            else:
                username_base = email.split('@', 1)[0][:40] or 'google_user'
                username = username_base
                while self.check_exist(username):
                    username = f'{username_base}_{token_urlsafe(4).lower()}'[:50]

                user_obj = UserModel(
                    username=username,
                    email=email,
                    password_hash=token_urlsafe(32),
                    full_name=full_name,
                    avatar_url=avatar_url,
                    status='active',
                    email_verified=True
                )
                self.session.add(user_obj)
                self.session.flush()

                role_obj = self.session.query(RoleModel).filter_by(code='participant').first()
                if role_obj is None:
                    role_obj = RoleModel(
                        code='participant',
                        name='Participant',
                        description='Default participant role',
                    )
                    self.session.add(role_obj)
                    self.session.flush()
                self.session.execute(insert(user_roles).values(user_id=user_obj.id, role_id=role_obj.id))

            self.session.commit()
            return Auth(
                id=user_obj.id,
                username=user_obj.username,
                password='',
                passwordcomfirm='',
                email=user_obj.email,
                role=self.get_user_role(user_obj.id) or 'participant',
                full_name=user_obj.full_name,
                email_verified=user_obj.email_verified
            )
        except Exception as e:
            self.session.rollback()
            print(f"Error logging in with Google: {e}")
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
                full_name=user_obj.full_name,
                avatar_url=getattr(user_obj, 'avatar_url', None),
                bio=getattr(user_obj, 'bio', None),
                created_at=user_obj.created_at.isoformat() if user_obj.created_at else None,
                email_verified=user_obj.email_verified
            )
        except Exception as e:
            print(f"Error fetching user by id: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Auth]:
        try:
            user_obj = self.session.query(UserModel).filter_by(email=email).first()
            if not user_obj:
                return None

            role_code = self.get_user_role(user_obj.id) or 'participant'
            return Auth(
                id=user_obj.id,
                username=user_obj.username,
                password='',
                passwordcomfirm='',
                email=user_obj.email,
                role=role_code,
                full_name=user_obj.full_name,
                avatar_url=getattr(user_obj, 'avatar_url', None),
                bio=getattr(user_obj, 'bio', None),
                created_at=user_obj.created_at.isoformat() if user_obj.created_at else None,
                email_verified=user_obj.email_verified
            )
        except Exception as e:
            print(f"Error fetching user by email: {e}")
            return None

    def update_profile(self, user_id: int, full_name: Optional[str] = None, bio: Optional[str] = None, avatar_url: Optional[str] = None) -> Optional[Auth]:
        try:
            user_obj = self.session.query(UserModel).filter_by(id=user_id).first()
            if not user_obj:
                return None

            if full_name is not None:
                user_obj.full_name = full_name
            if bio is not None:
                user_obj.bio = bio
            if avatar_url is not None:
                user_obj.avatar_url = avatar_url

            self.session.commit()
            self.session.refresh(user_obj)

            role_code = self.get_user_role(user_id) or 'participant'
            return Auth(
                id=user_obj.id,
                username=user_obj.username,
                password='',
                passwordcomfirm='',
                email=user_obj.email,
                role=role_code,
                full_name=user_obj.full_name,
                avatar_url=user_obj.avatar_url,
                bio=user_obj.bio,
                created_at=user_obj.created_at.isoformat() if user_obj.created_at else None,
                email_verified=user_obj.email_verified
            )
        except Exception as e:
            self.session.rollback()
            print(f"Error updating user profile: {e}")
            return None

    def update_email_verified(self, user_id: int, verified: bool = True) -> bool:
        try:
            user_obj = self.session.query(UserModel).filter_by(id=user_id).first()
            if not user_obj:
                return False
            user_obj.email_verified = verified
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error updating email verification: {e}")
            return False

    def update_password(self, user_id: int, password_hash: str) -> bool:
        try:
            user_obj = self.session.query(UserModel).filter_by(id=user_id).first()
            if not user_obj:
                return False
            user_obj.password_hash = password_hash
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"Error updating password: {e}")
            return False

    def update_status(self, user_id: int, status: str) -> bool:
        try:
            user_obj = self.session.query(UserModel).filter_by(id=user_id).first()
            if not user_obj:
                return False
            user_obj.status = status
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()

            print(f"Error updating status: {e}")

            print(f"Error updating user status: {e}")
            return False

