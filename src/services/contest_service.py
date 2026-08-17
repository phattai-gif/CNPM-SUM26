import re
from datetime import datetime
from typing import List, Optional
try:
    from domain.models.icontest_repository import IContestRepository
    from domain.contest import Contest, Round, Criteria
except ImportError:
    from domain.models.icontest_repository import IContestRepository
    from domain.contest import Contest, Round, Criteria


class ContestService:
    def __init__(self, repository: IContestRepository):
        self.repository = repository

    def _generate_slug(self, title: str) -> str:
        base_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        timestamp = int(datetime.utcnow().timestamp())
        return f"{base_slug}-{timestamp}"

    def _parse_datetime(self, val):
        if isinstance(val, datetime):
            return val
        if isinstance(val, str) and val.strip():
            try:
                return datetime.fromisoformat(val)
            except Exception:
                return None
        return None

    def _check_ownership(self, contest: Contest, user_id: int, user_role: str):
        if user_role == 'admin':
            return
        if contest.created_by != user_id:
            raise PermissionError("Bạn không có quyền thao tác trên cuộc thi này.")

    def create_contest(self, data: dict, user_id: int) -> Contest:
        title = data.get('title')
        if not title:
            raise ValueError("Tiêu đề cuộc thi không được để trống.")

        slug = data.get('slug')
        if not slug:
            slug = self._generate_slug(title)

        start_date = self._parse_datetime(data.get('start_date'))
        end_date = self._parse_datetime(data.get('end_date'))

        if start_date and end_date and end_date < start_date:
            raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu.")

        contest = Contest(
            title=title,
            slug=slug,
            description=data.get('description'),
            rules=data.get('rules'),
            banner_url=data.get('banner_url'),
            created_by=user_id,
            status=data.get('status', 'draft'),
            start_date=start_date,
            end_date=end_date
        )
        return self.repository.create_contest(contest)

    def get_contest(self, contest_id: int) -> Optional[Contest]:
        return self.repository.get_contest_by_id(contest_id)

    def list_organizer_contests(self, user_id: int) -> List[Contest]:
        return self.repository.get_contests_by_organizer(user_id)

    def update_contest(self, contest_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Contest:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        updates = {}
        for field in ['title', 'description', 'rules', 'banner_url', 'status']:
            if field in data:
                updates[field] = data[field]

        if 'start_date' in data:
            updates['start_date'] = self._parse_datetime(data['start_date'])
        if 'end_date' in data:
            updates['end_date'] = self._parse_datetime(data['end_date'])

        # Validate dates if both updated or existing
        new_start = updates.get('start_date', contest.start_date)
        new_end = updates.get('end_date', contest.end_date)
        if new_start and new_end and new_end < new_start:
            raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu.")

        updated = self.repository.update_contest(contest_id, updates)
        return updated

    def update_rules(self, contest_id: int, rules: str, user_id: int, user_role: str = 'organizer') -> Contest:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        return self.repository.update_rules(contest_id, rules)

    def delete_contest(self, contest_id: int, user_id: int, user_role: str = 'organizer') -> bool:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        return self.repository.delete_contest(contest_id)

    def create_round(self, contest_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Round:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        title = data.get('title')
        if not title:
            raise ValueError("Tên vòng thi không được để trống.")

        start_date = self._parse_datetime(data.get('start_date'))
        end_date = self._parse_datetime(data.get('end_date'))

        initial_criteria = []
        if 'criteria' in data and isinstance(data['criteria'], list):
            for c in data['criteria']:
                initial_criteria.append(Criteria(
                    name=c.get('name', ''),
                    description=c.get('description'),
                    max_score=c.get('max_score', 10.0),
                    weight=c.get('weight', 1.0)
                ))

        round_obj = Round(
            contest_id=contest_id,
            round_number=data.get('round_number', len(contest.rounds) + 1),
            title=title,
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            weight=data.get('weight', 1.0),
            status=data.get('status', 'upcoming'),
            criteria=initial_criteria
        )
        return self.repository.create_round(round_obj)

    def update_round(self, contest_id: int, round_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Round:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("Không tìm thấy vòng thi thuộc cuộc thi này.")

        updates = {}
        for field in ['title', 'description', 'round_number', 'weight', 'status']:
            if field in data:
                updates[field] = data[field]

        if 'start_date' in data:
            updates['start_date'] = self._parse_datetime(data['start_date'])
        if 'end_date' in data:
            updates['end_date'] = self._parse_datetime(data['end_date'])

        return self.repository.update_round(round_id, updates)

    def delete_round(self, contest_id: int, round_id: int, user_id: int, user_role: str = 'organizer') -> bool:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("Không tìm thấy vòng thi thuộc cuộc thi này.")

        return self.repository.delete_round(round_id)

    def create_criteria(self, contest_id: int, round_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Criteria:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("Không tìm thấy vòng thi thuộc cuộc thi này.")

        name = data.get('name')
        if not name:
            raise ValueError("Tên tiêu chí không được để trống.")

        criteria_obj = Criteria(
            round_id=round_id,
            name=name,
            description=data.get('description'),
            max_score=data.get('max_score', 10.0),
            weight=data.get('weight', 1.0)
        )
        return self.repository.create_criteria(criteria_obj)

    def update_criteria(self, contest_id: int, round_id: int, criteria_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Criteria:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("Không tìm thấy vòng thi thuộc cuộc thi này.")

        crit_obj = self.repository.get_criteria_by_id(criteria_id)
        if not crit_obj or crit_obj.round_id != round_id:
            raise ValueError("Không tìm thấy tiêu chí chấm điểm thuộc vòng thi này.")

        updates = {}
        for field in ['name', 'description', 'max_score', 'weight']:
            if field in data:
                updates[field] = data[field]

        return self.repository.update_criteria(criteria_id, updates)

    def delete_criteria(self, contest_id: int, round_id: int, criteria_id: int, user_id: int, user_role: str = 'organizer') -> bool:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("Không tìm thấy vòng thi thuộc cuộc thi này.")

        crit_obj = self.repository.get_criteria_by_id(criteria_id)
        if not crit_obj or crit_obj.round_id != round_id:
            raise ValueError("Không tìm thấy tiêu chí chấm điểm thuộc vòng thi này.")

        return self.repository.delete_criteria(criteria_id)

    def update_contest_configuration(self, contest_id: int, config_data: dict, user_id: int, user_role: str = 'organizer') -> Contest:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("Không tìm thấy cuộc thi.")
        self._check_ownership(contest, user_id, user_role)

        rules = config_data.get('rules')
        rounds_data = config_data.get('rounds')

        return self.repository.update_contest_configuration(contest_id, rules, rounds_data)
