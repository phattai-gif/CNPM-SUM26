from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from .submission import Submission


class ISubmissionRepository(ABC):
    @abstractmethod
    def add(self, submission: Submission) -> Submission:
        pass

    @abstractmethod
    def get_by_id(self, submission_id: int) -> Optional[Submission]:
        pass

    @abstractmethod
    def get_by_id_with_details(self, submission_id: int) -> Optional[Tuple[Submission, Optional[object], Optional[object]]]:
        pass

    @abstractmethod
    def list(self) -> List[Submission]:
        pass

    @abstractmethod
    def update(self, submission: Submission) -> Submission:
        pass

    @abstractmethod
    def delete(self, submission_id: int) -> None:
        pass
