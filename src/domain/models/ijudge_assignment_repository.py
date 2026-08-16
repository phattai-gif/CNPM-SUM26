from abc import ABC, abstractmethod
from typing import List, Optional, Any
from datetime import datetime

try:
    from domain.contest import JudgeAssignment
except ImportError:
    from domain.contest import JudgeAssignment


class IJudgeAssignmentRepository(ABC):
    @abstractmethod
    def assign_judge(self, round_id: int, judge_id: int, submission_id: Optional[int] = None, status: str = 'assigned') -> JudgeAssignment:
        pass

    @abstractmethod
    def get_assignment(self, round_id: int, judge_id: int, submission_id: Optional[int] = None) -> Optional[JudgeAssignment]:
        pass

    @abstractmethod
    def get_assignments_by_round(self, round_id: int) -> List[JudgeAssignment]:
        pass

    @abstractmethod
    def remove_judge_assignment(self, round_id: int, judge_id: int, submission_id: Optional[int] = None) -> bool:
        pass

    @abstractmethod
    def get_available_judges(self) -> List[dict]:
        pass

    @abstractmethod
    def get_assignments_by_judge(self, judge_id: int) -> List[JudgeAssignment]:
        pass
