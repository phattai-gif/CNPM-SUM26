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
        try:
            owner_id = int(contest.created_by)
        except (TypeError, ValueError):
            owner_id = contest.created_by
        try:
            actor_id = int(user_id)
        except (TypeError, ValueError):
            actor_id = user_id
        if owner_id != actor_id:
            raise PermissionError("Báº¡n khÃ´ng cÃ³ quyá»n thao tÃ¡c trÃªn cuá»™c thi nÃ y.")

    def _normalize_contest_status(self, status_value: Optional[str]) -> str:
        allowed = {'draft', 'published', 'active', 'completed', 'archived'}
        if status_value is None:
            return 'draft'
        normalized = str(status_value).strip().lower()
        aliases = {
            'ended': 'completed',
            'done': 'completed',
            'open': 'active',
            'live': 'active',
        }
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in allowed else 'draft'

    def _normalize_round_status(self, status_value: Optional[str]) -> str:
        allowed = {'upcoming', 'ongoing', 'completed'}
        if status_value is None:
            return 'upcoming'
        normalized = str(status_value).strip().lower()
        aliases = {
            'open': 'ongoing',
            'active': 'ongoing',
            'in_progress': 'ongoing',
            'closed': 'completed',
            'ended': 'completed',
            'done': 'completed',
            'draft': 'upcoming',
            'pending': 'upcoming',
        }
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in allowed else 'upcoming'

    def _coerce_int(self, value, default: int, minimum: Optional[int] = None) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        if minimum is not None and parsed < minimum:
            return default
        return parsed

    def _coerce_float(self, value, default: float, minimum: Optional[float] = None) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        if minimum is not None and parsed < minimum:
            return default
        return parsed

    def _next_collection_id(self, items: List[dict]) -> int:
        max_id = 0
        for item in items:
            try:
                value = int(item.get('id'))
            except (TypeError, ValueError, AttributeError):
                value = 0
            if value > max_id:
                max_id = value
        return max_id + 1

    def _normalize_categories(self, categories) -> List[dict]:
        if categories is None:
            return []

        if isinstance(categories, str):
            categories = [item.strip() for item in categories.split(',') if item.strip()]

        normalized = []
        for item in categories:
            if isinstance(item, str):
                name = item.strip()
                if not name:
                    continue
                normalized.append({
                    'id': self._next_collection_id(normalized),
                    'name': name,
                    'description': ''
                })
                continue

            if not isinstance(item, dict):
                continue

            name = str(item.get('name', '')).strip()
            if not name:
                continue

            description = str(item.get('description', '') or '').strip()

            try:
                category_id = int(item.get('id'))
            except (TypeError, ValueError):
                category_id = self._next_collection_id(normalized)

            normalized.append({
                'id': category_id,
                'name': name,
                'description': description,
            })

        return normalized

    def _normalize_awards(self, awards) -> List[dict]:
        if awards is None:
            return []

        if isinstance(awards, dict):
            awards = [awards]

        normalized = []
        for item in awards:
            if not isinstance(item, dict):
                continue

            title = str(item.get('title', '')).strip()
            if not title:
                continue

            description = str(item.get('description', '') or '').strip()
            prize = str(item.get('prize', '') or '').strip()

            try:
                rank = int(item.get('rank'))
            except (TypeError, ValueError):
                rank = len(normalized) + 1

            try:
                award_id = int(item.get('id'))
            except (TypeError, ValueError):
                award_id = self._next_collection_id(normalized)

            normalized.append({
                'id': award_id,
                'rank': rank,
                'title': title,
                'prize': prize,
                'description': description,
            })

        normalized.sort(key=lambda x: (x.get('rank', 999999), x.get('id', 999999)))
        return normalized

    def create_contest(self, data: dict, user_id: int) -> Contest:
        title = data.get('title')
        if not title:
            raise ValueError("TiÃªu Ä‘á» cuá»™c thi khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")

        slug = data.get('slug')
        if not slug:
            slug = self._generate_slug(title)

        start_date = self._parse_datetime(data.get('start_date'))
        end_date = self._parse_datetime(data.get('end_date'))

        if start_date and end_date and end_date < start_date:
            raise ValueError("Thá»i gian káº¿t thÃºc pháº£i sau thá»i gian báº¯t Ä‘áº§u.")

        contest = Contest(
            title=title,
            slug=slug,
            description=data.get('description'),
            rules=data.get('rules'),
            banner_url=data.get('banner_url'),
            created_by=user_id,
            status=self._normalize_contest_status(data.get('status', 'draft')),
            start_date=start_date,
            end_date=end_date,
            categories=self._normalize_categories(data.get('categories')),
            awards=self._normalize_awards(data.get('awards'))
        )
        return self.repository.create_contest(contest)

    def get_contest(self, contest_id: int) -> Optional[Contest]:
        return self.repository.get_contest_by_id(contest_id)

    def list_organizer_contests(self, user_id: int) -> List[Contest]:
        return self.repository.get_contests_by_organizer(user_id)

    def update_contest(self, contest_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Contest:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        updates = {}
        for field in ['title', 'description', 'rules', 'banner_url', 'status']:
            if field in data:
                updates[field] = (
                    self._normalize_contest_status(data[field])
                    if field == 'status'
                    else data[field]
                )

        if 'categories' in data:
            updates['categories_json'] = self._normalize_categories(data.get('categories'))
        if 'awards' in data:
            updates['awards_json'] = self._normalize_awards(data.get('awards'))

        if 'start_date' in data:
            updates['start_date'] = self._parse_datetime(data['start_date'])
        if 'end_date' in data:
            updates['end_date'] = self._parse_datetime(data['end_date'])

        # Validate dates if both updated or existing
        new_start = updates.get('start_date', contest.start_date)
        new_end = updates.get('end_date', contest.end_date)
        if new_start and new_end and new_end < new_start:
            raise ValueError("Thá»i gian káº¿t thÃºc pháº£i sau thá»i gian báº¯t Ä‘áº§u.")

        updated = self.repository.update_contest(contest_id, updates)
        return updated

    def list_categories(self, contest_id: int, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)
        return self._normalize_categories(contest.categories)

    def create_category(self, contest_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        name = str(data.get('name', '')).strip()
        description = str(data.get('description', '') or '').strip()
        if not name:
            raise ValueError("TÃªn danh má»¥c khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")

        categories = self._normalize_categories(contest.categories)
        new_item = {
            'id': self._next_collection_id(categories),
            'name': name,
            'description': description,
        }
        categories.append(new_item)
        self.repository.update_contest(contest_id, {'categories_json': categories})
        return categories

    def update_category(self, contest_id: int, category_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        categories = self._normalize_categories(contest.categories)
        target = next((item for item in categories if int(item.get('id', 0)) == int(category_id)), None)
        if not target:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y danh má»¥c.")

        if 'name' in data:
            name = str(data.get('name', '')).strip()
            if not name:
                raise ValueError("TÃªn danh má»¥c khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")
            target['name'] = name
        if 'description' in data:
            target['description'] = str(data.get('description', '') or '').strip()

        self.repository.update_contest(contest_id, {'categories_json': categories})
        return categories

    def delete_category(self, contest_id: int, category_id: int, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        categories = self._normalize_categories(contest.categories)
        filtered = [item for item in categories if int(item.get('id', 0)) != int(category_id)]
        if len(filtered) == len(categories):
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y danh má»¥c.")

        self.repository.update_contest(contest_id, {'categories_json': filtered})
        return filtered

    def list_awards(self, contest_id: int, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)
        return self._normalize_awards(contest.awards)

    def create_award(self, contest_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        title = str(data.get('title', '')).strip()
        if not title:
            raise ValueError("TÃªn giáº£i thÆ°á»Ÿng khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")

        rank = self._coerce_int(data.get('rank'), default=0, minimum=1)
        if rank <= 0:
            rank = None

        awards = self._normalize_awards(contest.awards)
        if rank is None:
            rank = (max([int(item.get('rank', 0)) for item in awards], default=0) + 1)

        award = {
            'id': self._next_collection_id(awards),
            'rank': rank,
            'title': title,
            'prize': str(data.get('prize', '') or '').strip(),
            'description': str(data.get('description', '') or '').strip(),
        }
        awards.append(award)
        awards = self._normalize_awards(awards)
        self.repository.update_contest(contest_id, {'awards_json': awards})
        return awards

    def update_award(self, contest_id: int, award_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        awards = self._normalize_awards(contest.awards)
        target = next((item for item in awards if int(item.get('id', 0)) == int(award_id)), None)
        if not target:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y giáº£i thÆ°á»Ÿng.")

        if 'title' in data:
            title = str(data.get('title', '')).strip()
            if not title:
                raise ValueError("TÃªn giáº£i thÆ°á»Ÿng khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")
            target['title'] = title
        if 'description' in data:
            target['description'] = str(data.get('description', '') or '').strip()
        if 'prize' in data:
            target['prize'] = str(data.get('prize', '') or '').strip()
        if 'rank' in data:
            target['rank'] = self._coerce_int(data.get('rank'), default=int(target.get('rank', 1) or 1), minimum=1)

        awards = self._normalize_awards(awards)
        self.repository.update_contest(contest_id, {'awards_json': awards})
        return awards

    def delete_award(self, contest_id: int, award_id: int, user_id: int, user_role: str = 'organizer') -> List[dict]:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        awards = self._normalize_awards(contest.awards)
        filtered = [item for item in awards if int(item.get('id', 0)) != int(award_id)]
        if len(filtered) == len(awards):
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y giáº£i thÆ°á»Ÿng.")

        filtered = self._normalize_awards(filtered)
        self.repository.update_contest(contest_id, {'awards_json': filtered})
        return filtered

    def update_rules(self, contest_id: int, rules: str, user_id: int, user_role: str = 'organizer') -> Contest:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        return self.repository.update_rules(contest_id, rules)

    def delete_contest(self, contest_id: int, user_id: int, user_role: str = 'organizer') -> bool:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        return self.repository.delete_contest(contest_id)

    def create_round(self, contest_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Round:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        title = str(data.get('title', '')).strip()
        if not title:
            raise ValueError("TÃªn vÃ²ng thi khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")

        start_date = self._parse_datetime(data.get('start_date'))
        end_date = self._parse_datetime(data.get('end_date'))

        if start_date and end_date and end_date < start_date:
            raise ValueError("Thá»i gian káº¿t thÃºc vÃ²ng thi pháº£i sau thá»i gian báº¯t Ä‘áº§u.")

        initial_criteria = []
        if 'criteria' in data and isinstance(data['criteria'], list):
            for c in data['criteria']:
                name = str(c.get('name', '')).strip()
                if not name:
                    continue
                initial_criteria.append(Criteria(
                    name=name,
                    description=c.get('description'),
                    max_score=self._coerce_float(c.get('max_score'), 10.0, minimum=0.0),
                    weight=self._coerce_float(c.get('weight'), 1.0, minimum=0.0)
                ))

        round_obj = Round(
            contest_id=contest_id,
            round_number=self._coerce_int(data.get('round_number'), len(contest.rounds) + 1, minimum=1),
            title=title,
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            weight=self._coerce_float(data.get('weight'), 1.0, minimum=0.0),
            status=self._normalize_round_status(data.get('status', 'upcoming')),
            criteria=initial_criteria
        )
        return self.repository.create_round(round_obj)

    def update_round(self, contest_id: int, round_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Round:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        updates = {}
        if 'title' in data:
            title = str(data.get('title', '')).strip()
            if not title:
                raise ValueError("TÃªn vÃ²ng thi khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")
            updates['title'] = title
        if 'description' in data:
            updates['description'] = data.get('description')
        if 'round_number' in data:
            updates['round_number'] = self._coerce_int(data.get('round_number'), round_obj.round_number or 1, minimum=1)
        if 'weight' in data:
            updates['weight'] = self._coerce_float(data.get('weight'), float(round_obj.weight or 1.0), minimum=0.0)
        if 'status' in data:
            updates['status'] = self._normalize_round_status(data.get('status'))

        if 'start_date' in data:
            updates['start_date'] = self._parse_datetime(data['start_date'])
        if 'end_date' in data:
            updates['end_date'] = self._parse_datetime(data['end_date'])

        new_start = updates.get('start_date', round_obj.start_date)
        new_end = updates.get('end_date', round_obj.end_date)
        if new_start and new_end and new_end < new_start:
            raise ValueError("Thá»i gian káº¿t thÃºc vÃ²ng thi pháº£i sau thá»i gian báº¯t Ä‘áº§u.")

        return self.repository.update_round(round_id, updates)

    def delete_round(self, contest_id: int, round_id: int, user_id: int, user_role: str = 'organizer') -> bool:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        return self.repository.delete_round(round_id)

    def create_criteria(self, contest_id: int, round_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Criteria:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        name = str(data.get('name', '')).strip()
        if not name:
            raise ValueError("TÃªn tiÃªu chÃ­ khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")

        criteria_obj = Criteria(
            round_id=round_id,
            name=name,
            description=data.get('description'),
            max_score=self._coerce_float(data.get('max_score'), 10.0, minimum=0.0),
            weight=self._coerce_float(data.get('weight'), 1.0, minimum=0.0)
        )
        return self.repository.create_criteria(criteria_obj)

    def update_criteria(self, contest_id: int, round_id: int, criteria_id: int, data: dict, user_id: int, user_role: str = 'organizer') -> Criteria:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        crit_obj = self.repository.get_criteria_by_id(criteria_id)
        if not crit_obj or crit_obj.round_id != round_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm thuá»™c vÃ²ng thi nÃ y.")

        updates = {}
        if 'name' in data:
            name = str(data.get('name', '')).strip()
            if not name:
                raise ValueError("TÃªn tiÃªu chÃ­ khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")
            updates['name'] = name
        if 'description' in data:
            updates['description'] = data.get('description')
        if 'max_score' in data:
            updates['max_score'] = self._coerce_float(data.get('max_score'), float(crit_obj.max_score or 10.0), minimum=0.0)
        if 'weight' in data:
            updates['weight'] = self._coerce_float(data.get('weight'), float(crit_obj.weight or 1.0), minimum=0.0)

        return self.repository.update_criteria(criteria_id, updates)

    def delete_criteria(self, contest_id: int, round_id: int, criteria_id: int, user_id: int, user_role: str = 'organizer') -> bool:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        round_obj = self.repository.get_round_by_id(round_id)
        if not round_obj or round_obj.contest_id != contest_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y vÃ²ng thi thuá»™c cuá»™c thi nÃ y.")

        crit_obj = self.repository.get_criteria_by_id(criteria_id)
        if not crit_obj or crit_obj.round_id != round_id:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y tiÃªu chÃ­ cháº¥m Ä‘iá»ƒm thuá»™c vÃ²ng thi nÃ y.")

        return self.repository.delete_criteria(criteria_id)

    def update_contest_configuration(self, contest_id: int, config_data: dict, user_id: int, user_role: str = 'organizer') -> Contest:
        contest = self.repository.get_contest_by_id(contest_id)
        if not contest:
            raise ValueError("KhÃ´ng tÃ¬m tháº¥y cuá»™c thi.")
        self._check_ownership(contest, user_id, user_role)

        rules = config_data.get('rules')
        rounds_data = config_data.get('rounds')

        sanitized_rounds = None
        if isinstance(rounds_data, list):
            sanitized_rounds = []
            for index, item in enumerate(rounds_data, start=1):
                if not isinstance(item, dict):
                    continue
                title = str(item.get('title', '')).strip() or f'Round {index}'
                criteria = []
                for c in (item.get('criteria') or []):
                    if not isinstance(c, dict):
                        continue
                    name = str(c.get('name', '')).strip()
                    if not name:
                        continue
                    criteria.append({
                        'name': name,
                        'description': c.get('description'),
                        'max_score': self._coerce_float(c.get('max_score'), 10.0, minimum=0.0),
                        'weight': self._coerce_float(c.get('weight'), 1.0, minimum=0.0),
                    })

                sanitized_rounds.append({
                    'round_number': self._coerce_int(item.get('round_number'), index, minimum=1),
                    'title': title,
                    'description': item.get('description'),
                    'start_date': item.get('start_date'),
                    'end_date': item.get('end_date'),
                    'weight': self._coerce_float(item.get('weight'), 1.0, minimum=0.0),
                    'status': self._normalize_round_status(item.get('status')),
                    'criteria': criteria,
                })

        return self.repository.update_contest_configuration(contest_id, rules, sanitized_rounds)

