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