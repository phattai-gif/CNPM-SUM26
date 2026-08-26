from typing import Optional
from domain.models.auth import Auth
from domain.models.iauth_repository import IAuthRepository


class AuthService:
    def __init__(self, repository: IAuthRepository):
        self.repository = repository

    def register(self, username: str, password: str, email: str, role: str = 'participant', full_name: str = None) -> Optional[Auth]:
        if self.repository.check_exist(username):
            return None  # Username already exists
        if self.repository.check_email_exist(email):
            return None  # Email already exists

        auth = Auth(
            username=username,
            password=password,
            passwordcomfirm=password,
            email=email,
            role=role,
            full_name=full_name
        )
        return self.repository.register(auth)

    def login(self, username: str, password: str) -> Optional[Auth]:
        auth = Auth(
            username=username,
            password=password,
            passwordcomfirm=password,
            email=""
        )
        return self.repository.login(auth)

    def login_google(self, email: str, full_name: str = None, avatar_url: str = None) -> Optional[Auth]:
        return self.repository.login_google(email, full_name, avatar_url)

    def check_exist(self, username: str) -> bool:
        return self.repository.check_exist(username)

    def check_email_exist(self, email: str) -> bool:
        return self.repository.check_email_exist(email)

    def get_user_role(self, user_id: int) -> Optional[str]:
        return self.repository.get_user_role(user_id)

    def get_user_by_id(self, user_id: int) -> Optional[Auth]:
        return self.repository.get_user_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[Auth]:
        return self.repository.get_user_by_email(email)

    def update_profile(self, user_id: int, full_name: Optional[str] = None, bio: Optional[str] = None, avatar_url: Optional[str] = None) -> Optional[Auth]:
        return self.repository.update_profile(user_id=user_id, full_name=full_name, bio=bio, avatar_url=avatar_url)

    def update_password(self, user_id: int, password_hash: str) -> bool:
        return self.repository.update_password(user_id, password_hash)

    def update_status(self, user_id: int, status: str) -> bool:
        return self.repository.update_status(user_id, status)

