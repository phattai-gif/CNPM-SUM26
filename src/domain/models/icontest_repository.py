from abc import ABC, abstractmethod
from typing import List, Optional, Any

try:
    from src.domain.contest import Contest, Round, Criteria
except ImportError:
    from domain.contest import Contest, Round, Criteria


class IContestRepository(ABC):
    @abstractmethod
    def create_contest(self, contest: Contest) -> Contest:
        pass

    @abstractmethod
    def get_contest_by_id(self, contest_id: int) -> Optional[Contest]:
        pass

    @abstractmethod
    def get_contests_by_organizer(self, created_by: int) -> List[Contest]:
        pass

    @abstractmethod
    def update_contest(self, contest_id: int, data: dict) -> Optional[Contest]:
        pass

    @abstractmethod
    def update_rules(self, contest_id: int, rules: str) -> Optional[Contest]:
        pass

    @abstractmethod
    def delete_contest(self, contest_id: int) -> bool:
        pass

    @abstractmethod
    def create_round(self, round_obj: Round) -> Round:
        pass

    @abstractmethod
    def get_round_by_id(self, round_id: int) -> Optional[Round]:
        pass

    @abstractmethod
    def get_rounds_by_contest_id(self, contest_id: int) -> List[Round]:
        pass

    @abstractmethod
    def update_round(self, round_id: int, data: dict) -> Optional[Round]:
        pass

    @abstractmethod
    def delete_round(self, round_id: int) -> bool:
        pass

    @abstractmethod
    def create_criteria(self, criteria_obj: Criteria) -> Criteria:
        pass

    @abstractmethod
    def get_criteria_by_id(self, criteria_id: int) -> Optional[Criteria]:
        pass

    @abstractmethod
    def get_criteria_by_round_id(self, round_id: int) -> List[Criteria]:
        pass

    @abstractmethod
    def update_criteria(self, criteria_id: int, data: dict) -> Optional[Criteria]:
        pass

    @abstractmethod
    def delete_criteria(self, criteria_id: int) -> bool:
        pass

    @abstractmethod
    def update_contest_configuration(self, contest_id: int, rules: Optional[str], rounds_data: List[dict]) -> Optional[Contest]:
        pass
