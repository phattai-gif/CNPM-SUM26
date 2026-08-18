from typing import List, Optional

try:
    from domain.models.ijudge_assignment_repository import IJudgeAssignmentRepository
    from domain.models.icontest_repository import IContestRepository
    from domain.contest import JudgeAssignment, Contest, Round
except ImportError:
    from domain.models.ijudge_assignment_repository import IJudgeAssignmentRepository
    from domain.models.icontest_repository import IContestRepository
    from domain.contest import JudgeAssignment, Contest, Round


class JudgeAssignmentService:
    def __init__(self, judge_repo: IJudgeAssignmentRepository, contest_repo: IContestRepository):
        self.judge_repo = judge_repo
        self.contest_repo = contest_repo

    def _check_ownership(self, contest: Contest, user_id: int, user_role: str):
        if user_role == 'admin':
            return
        if contest.created_by != user_id:
            raise PermissionError("Báº¡n khÃ´ng cÃ³ quyá»n thao tÃ¡c trÃªn cuá»™c thi nÃ y.")

    def assign_judge_to_round(
        self,
        contest_id: int,
        round_id: int,
        judge_id: int,
        submission_id: Optional[int] = None,
        user_id: int = 0,
        user_role: str = 'organizer'
    ) -> JudgeAssignment:
        contest = self.contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.contest_repo.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        return self.judge_repo.assign_judge(
            round_id=round_id,
            judge_id=judge_id,
            submission_id=submission_id
        )

    def batch_assign_judges_to_round(
        self,
        contest_id: int,
        round_id: int,
        judge_ids: List[int],
        submission_id: Optional[int] = None,
        user_id: int = 0,
        user_role: str = 'organizer'
    ) -> List[JudgeAssignment]:
        contest = self.contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.contest_repo.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        assigned_list = []
        for j_id in judge_ids:
            assignment = self.judge_repo.assign_judge(
                round_id=round_id,
                judge_id=j_id,
                submission_id=submission_id
            )
            assigned_list.append(assignment)

        return assigned_list

    def get_round_judges(
        self,
        contest_id: int,
        round_id: int,
        user_id: int = 0,
        user_role: str = 'organizer'
    ) -> List[JudgeAssignment]:
        contest = self.contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.contest_repo.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        return self.judge_repo.get_assignments_by_round(round_id)

    def remove_judge_from_round(
        self,
        contest_id: int,
        round_id: int,
        judge_id: int,
        submission_id: Optional[int] = None,
        user_id: int = 0,
        user_role: str = 'organizer'
    ) -> bool:
        contest = self.contest_repo.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.contest_repo.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        return self.judge_repo.remove_judge_assignment(round_id, judge_id, submission_id)

    def get_available_judges(self) -> List[dict]:
        return self.judge_repo.get_available_judges()

    def get_judge_assignments(self, judge_id: int) -> List[JudgeAssignment]:
        return self.judge_repo.get_assignments_by_judge(judge_id)

