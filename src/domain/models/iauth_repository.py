from abc import ABC, abstractmethod
from typing import List, Optional
from .auth import Auth


class IAuthRepository(ABC):
    @abstractmethod
    def login(self, auth: Auth) -> Auth:
        pass

    @abstractmethod
    def register(self, auth: Auth) -> Optional[Auth]:
        pass

    @abstractmethod
    def check_exist(self, username: str) -> bool:
        pass

    @abstractmethod
    def check_email_exist(self, email: str) -> bool:
        pass

    @abstractmethod
    def get_user_role(self, user_id: int) -> Optional[str]:
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: int) -> Optional[Auth]:
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> Optional[Auth]:
        pass

    @abstractmethod
    def update_profile(self, user_id: int, full_name: Optional[str] = None, bio: Optional[str] = None, avatar_url: Optional[str] = None) -> Optional[Auth]:
        pass

    @abstractmethod
    def update_password(self, user_id: int, password_hash: str) -> bool:
        pass

    @abstractmethod
    def update_status(self, user_id: int, status: str) -> bool:
        pass
