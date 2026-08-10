from abc import ABC, abstractmethod
from typing import List, Optional

from .submission import Submission


class ISubmissionRepository(ABC):
    @abstractmethod
    def add(self, submission: Submission) -> Submission:
        pass

    @abstractmethod
    def get_by_id(self, submission_id: int) -> Optional[Submission]:
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
