from typing import List, Optional
from datetime import datetime


class Criteria:
    def __init__(self, id: Optional[int] = None, round_id: Optional[int] = None, 
                 name: str = "", description: Optional[str] = None, 
                 max_score: float = 10.0, weight: float = 1.0, 
                 created_at: Optional[datetime] = None):
        self.id = id
        self.round_id = round_id
        self.name = name
        self.description = description
        self.max_score = max_score
        self.weight = weight
        self.created_at = created_at

    def to_dict(self):
        return {
            'id': self.id,
            'round_id': self.round_id,
            'name': self.name,
            'description': self.description,
            'max_score': float(self.max_score) if self.max_score is not None else 10.0,
            'weight': float(self.weight) if self.weight is not None else 1.0,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }


class Round:
    def __init__(self, id: Optional[int] = None, contest_id: Optional[int] = None, 
                 round_number: int = 1, title: str = "", description: Optional[str] = None, 
                 start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, 
                 weight: float = 1.0, status: str = 'upcoming', 
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None,
                 criteria: Optional[List[Criteria]] = None):
        self.id = id
        self.contest_id = contest_id
        self.round_number = round_number
        self.title = title
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.weight = weight
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.criteria = criteria if criteria is not None else []

    def to_dict(self):
        return {
            'id': self.id,
            'contest_id': self.contest_id,
            'round_number': self.round_number,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat() if isinstance(self.start_date, datetime) else self.start_date,
            'end_date': self.end_date.isoformat() if isinstance(self.end_date, datetime) else self.end_date,
            'weight': float(self.weight) if self.weight is not None else 1.0,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'criteria': [c.to_dict() for c in self.criteria]
        }


class Contest:
    def __init__(self, id: Optional[int] = None, title: str = "", slug: str = "", 
                 description: Optional[str] = None, rules: Optional[str] = None,
                 banner_url: Optional[str] = None, created_by: int = 0, 
                 status: str = 'draft', start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None, created_at: Optional[datetime] = None, 
                 updated_at: Optional[datetime] = None, rounds: Optional[List[Round]] = None):
        self.id = id
        self.title = title
        self.slug = slug
        self.description = description
        self.rules = rules
        self.banner_url = banner_url
        self.created_by = created_by
        self.status = status
        self.start_date = start_date
        self.end_date = end_date
        self.created_at = created_at
        self.updated_at = updated_at
        self.rounds = rounds if rounds is not None else []

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'rules': self.rules,
            'banner_url': self.banner_url,
            'created_by': self.created_by,
            'status': self.status,
            'start_date': self.start_date.isoformat() if isinstance(self.start_date, datetime) else self.start_date,
            'end_date': self.end_date.isoformat() if isinstance(self.end_date, datetime) else self.end_date,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'rounds': [r.to_dict() for r in self.rounds]
        }


class JudgeAssignment:
    def __init__(self, id: Optional[int] = None, round_id: int = 0,
                 submission_id: Optional[int] = None, judge_id: int = 0,
                 status: str = 'assigned', assigned_at: Optional[datetime] = None,
                 judge_name: Optional[str] = None, judge_email: Optional[str] = None,
                 judge_username: Optional[str] = None):
        self.id = id
        self.round_id = round_id
        self.submission_id = submission_id
        self.judge_id = judge_id
        self.status = status
        self.assigned_at = assigned_at
        self.judge_name = judge_name
        self.judge_email = judge_email
        self.judge_username = judge_username

    def to_dict(self):
        return {
            'id': self.id,
            'round_id': self.round_id,
            'submission_id': self.submission_id,
            'judge_id': self.judge_id,
            'status': self.status,
            'assigned_at': self.assigned_at.isoformat() if isinstance(self.assigned_at, datetime) else self.assigned_at,
            'judge_name': self.judge_name,
            'judge_email': self.judge_email,
            'judge_username': self.judge_username
        }

