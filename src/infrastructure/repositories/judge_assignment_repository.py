from typing import List, Optional
from datetime import datetime
import os
from sqlalchemy.orm import Session
from sqlalchemy import select

try:
    from domain.models.ijudge_assignment_repository import IJudgeAssignmentRepository
    from domain.contest import JudgeAssignment
    from infrastructure.models.app import JudgeAssignmentModel, UserModel, RoleModel, user_roles
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory
except ImportError:
    from domain.models.ijudge_assignment_repository import IJudgeAssignmentRepository
    from domain.contest import JudgeAssignment
    from infrastructure.models.app import JudgeAssignmentModel, UserModel, RoleModel, user_roles
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory


class JudgeAssignmentRepository(IJudgeAssignmentRepository):
    def __init__(self, session: Optional[Session] = None):
        self._session = None
        self._session_uri = None
        if session is not None:
            self._session = session
        else:
            try:
                self._session = db_factory.get_database('POSTGREE').session
                self._session_uri = self._current_database_uri()
            except Exception:
                from infrastructure.databases.postgres import session as pg_session
                self._session = pg_session

    @staticmethod
    def _current_database_uri():
        return os.environ.get("DATABASE_URI") or os.environ.get("POSTGREE_DATABASE_URL")

    @property
    def session(self):
        if self._session_uri is None:
            return self._session

        current_uri = self._current_database_uri()
        if self._session is None or current_uri != self._session_uri:
            self._session = db_factory.get_database('POSTGREE').session
            self._session_uri = current_uri
        return self._session

    @session.setter
    def session(self, value):
        self._session = value
        self._session_uri = None

    def _rollback_session(self):
        try:
            self.session.rollback()
        except Exception:
            pass

    def _to_domain_assignment(self, model: JudgeAssignmentModel, user_model: Optional[UserModel] = None) -> JudgeAssignment:
        if not model:
            return None
        
        judge_name = user_model.full_name if user_model else None
        judge_email = user_model.email if user_model else None
        judge_username = user_model.username if user_model else None

        return JudgeAssignment(
            id=model.id,
            round_id=model.round_id,
            submission_id=model.submission_id,
            judge_id=model.judge_id,
            status=model.status,
            assigned_at=model.assigned_at,
            judge_name=judge_name,
            judge_email=judge_email,
            judge_username=judge_username
        )

    def assign_judge(self, round_id: int, judge_id: int, submission_id: Optional[int] = None, status: str = 'assigned') -> JudgeAssignment:
        try:
            self._rollback_session()
            # Check existing assignment
            query = self.session.query(JudgeAssignmentModel).filter(
                JudgeAssignmentModel.round_id == round_id,
                JudgeAssignmentModel.judge_id == judge_id
            )
            if submission_id is not None:
                query = query.filter(JudgeAssignmentModel.submission_id == submission_id)
            else:
                query = query.filter(JudgeAssignmentModel.submission_id.is_(None))

            existing = query.first()
            if existing:
                user_model = self.session.query(UserModel).filter_by(id=judge_id).first()
                return self._to_domain_assignment(existing, user_model)

            model = JudgeAssignmentModel(
                round_id=round_id,
                judge_id=judge_id,
                submission_id=submission_id,
                status=status
            )
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)

            user_model = self.session.query(UserModel).filter_by(id=judge_id).first()
            return self._to_domain_assignment(model, user_model)
        except Exception as e:
            self._rollback_session()
            raise e

    def get_assignment(self, round_id: int, judge_id: int, submission_id: Optional[int] = None) -> Optional[JudgeAssignment]:
        try:
            self._rollback_session()
            query = self.session.query(JudgeAssignmentModel).filter(
                JudgeAssignmentModel.round_id == round_id,
                JudgeAssignmentModel.judge_id == judge_id
            )
            if submission_id is not None:
                query = query.filter(JudgeAssignmentModel.submission_id == submission_id)
            else:
                query = query.filter(JudgeAssignmentModel.submission_id.is_(None))

            model = query.first()
            if not model:
                return None
            user_model = self.session.query(UserModel).filter_by(id=judge_id).first()
            return self._to_domain_assignment(model, user_model)
        except Exception:
            self._rollback_session()
            return None

    def get_assignments_by_round(self, round_id: int) -> List[JudgeAssignment]:
        try:
            self._rollback_session()
            results = (
                self.session.query(JudgeAssignmentModel, UserModel)
                .outerjoin(UserModel, JudgeAssignmentModel.judge_id == UserModel.id)
                .filter(JudgeAssignmentModel.round_id == round_id)
                .all()
            )
            assignments = []
            for assignment_model, user_model in results:
                assignments.append(self._to_domain_assignment(assignment_model, user_model))
            return assignments
        except Exception:
            self._rollback_session()
            return []

    def remove_judge_assignment(self, round_id: int, judge_id: int, submission_id: Optional[int] = None) -> bool:
        try:
            self._rollback_session()
            query = self.session.query(JudgeAssignmentModel).filter(
                JudgeAssignmentModel.round_id == round_id,
                JudgeAssignmentModel.judge_id == judge_id
            )
            if submission_id is not None:
                query = query.filter(JudgeAssignmentModel.submission_id == submission_id)
            else:
                query = query.filter(JudgeAssignmentModel.submission_id.is_(None))

            models = query.all()
            if not models:
                return False
            for m in models:
                self.session.delete(m)
            self.session.commit()
            return True
        except Exception as e:
            self._rollback_session()
            raise e

    def get_available_judges(self) -> List[dict]:
        try:
            self._rollback_session()
            # Try to query users with role 'judge' via user_roles & roles table
            judge_users = (
                self.session.query(UserModel)
                .join(user_roles, UserModel.id == user_roles.c.user_id)
                .join(RoleModel, user_roles.c.role_id == RoleModel.id)
                .filter(RoleModel.code == 'judge')
                .all()
            )

            # Fallback: if no judge users found in join (or roles table empty), return all users as potential candidates
            if not judge_users:
                judge_users = self.session.query(UserModel).filter(UserModel.status == 'active').all()

            return [
                {
                    'id': u.id,
                    'username': u.username,
                    'email': u.email,
                    'full_name': u.full_name
                }
                for u in judge_users
            ]
        except Exception:
            self._rollback_session()
            return []

    def get_assignments_by_judge(self, judge_id: int) -> List[JudgeAssignment]:
        try:
            self._rollback_session()
            results = (
                self.session.query(JudgeAssignmentModel, UserModel)
                .outerjoin(UserModel, JudgeAssignmentModel.judge_id == UserModel.id)
                .filter(JudgeAssignmentModel.judge_id == judge_id)
                .all()
            )
            assignments = []
            for assignment_model, user_model in results:
                assignments.append(self._to_domain_assignment(assignment_model, user_model))
            return assignments
        except Exception:
            self._rollback_session()
            return []

