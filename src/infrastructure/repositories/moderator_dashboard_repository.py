from sqlalchemy import distinct, func, select

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import (
    AIFlagModel,
    ContestModel,
    JudgeAssignmentModel,
    RoundModel,
    SubmissionModel,
    UserModel,
)


class ModeratorDashboardRepository:
    def __init__(self, session=None):
        self.session = session or db_factory.get_database('POSTGREE').session

    def contest_ids_for_user(self, user_id):
        return [
            row[0]
            for row in self.session.query(ContestModel.id)
            .filter(ContestModel.created_by == user_id)
            .all()
        ]

    def all_contest_ids(self):
        return [row[0] for row in self.session.query(ContestModel.id).all()]

    def contest_exists(self, contest_id):
        return self.session.query(ContestModel.id).filter_by(id=contest_id).scalar() is not None

    def dashboard_metrics(self, contest_ids):
        if not contest_ids:
            return {
                'contest_count': 0,
                'participant_count': 0,
                'submission_count': 0,
                'judge_assignment_count': 0,
                'submission_statuses': {status: 0 for status in ('submitted', 'flagged', 'evaluated', 'rejected')},
                'ai_risk_counts': {risk: 0 for risk in ('safe', 'medium', 'high')},
                'pending_ai_review_count': 0,
            }

        submission_scope = (
            self.session.query(SubmissionModel)
            .join(RoundModel, SubmissionModel.round_id == RoundModel.id)
            .filter(RoundModel.contest_id.in_(contest_ids))
            .subquery()
        )
        status_counts = dict(
            self.session.query(submission_scope.c.status, func.count(submission_scope.c.id))
            .group_by(submission_scope.c.status)
            .all()
        )
        risk_counts = dict(
            self.session.query(AIFlagModel.risk_level, func.count(distinct(AIFlagModel.submission_id)))
            .join(submission_scope, AIFlagModel.submission_id == submission_scope.c.id)
            .group_by(AIFlagModel.risk_level)
            .all()
        )
        pending_ai = (
            self.session.query(func.count(distinct(AIFlagModel.submission_id)))
            .join(submission_scope, AIFlagModel.submission_id == submission_scope.c.id)
            .filter(AIFlagModel.status.in_(['pending', 'flagged']))
            .scalar()
            or 0
        )
        return {
            'contest_count': self.session.query(func.count(ContestModel.id)).filter(ContestModel.id.in_(contest_ids)).scalar() or 0,
            'participant_count': self.session.query(func.count(distinct(submission_scope.c.user_id))).scalar() or 0,
            'submission_count': self.session.query(func.count(submission_scope.c.id)).scalar() or 0,
            'judge_assignment_count': self.session.query(func.count(JudgeAssignmentModel.id))
                .filter(JudgeAssignmentModel.round_id.in_(
                    select(RoundModel.id).where(RoundModel.contest_id.in_(contest_ids))
                )).scalar() or 0,
            'submission_statuses': {status: int(status_counts.get(status, 0)) for status in ('submitted', 'flagged', 'evaluated', 'rejected')},
            'ai_risk_counts': {risk: int(risk_counts.get(risk, 0)) for risk in ('safe', 'medium', 'high')},
            'pending_ai_review_count': int(pending_ai),
        }

    def review_queue(self, contest_ids, page, per_page, status=None, ai_risk=None):
        latest_flag_id = (
            select(func.max(AIFlagModel.id))
            .where(AIFlagModel.submission_id == SubmissionModel.id)
            .correlate(SubmissionModel)
            .scalar_subquery()
        )
        query = (
            self.session.query(SubmissionModel, ContestModel, UserModel, AIFlagModel)
            .join(RoundModel, SubmissionModel.round_id == RoundModel.id)
            .join(ContestModel, RoundModel.contest_id == ContestModel.id)
            .join(UserModel, SubmissionModel.user_id == UserModel.id)
            .outerjoin(AIFlagModel, AIFlagModel.id == latest_flag_id)
            .filter(ContestModel.id.in_(contest_ids))
            .filter(SubmissionModel.status.in_(['submitted', 'flagged']))
        )
        if status:
            query = query.filter(SubmissionModel.status == status)
        if ai_risk:
            query = query.filter(AIFlagModel.risk_level == ai_risk)

        total = query.count()
        rows = (
            query.order_by(SubmissionModel.submitted_at.asc(), SubmissionModel.id.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        items = []
        for submission, contest, user, ai_flag in rows:
            items.append({
                'id': submission.id,
                'contest_id': contest.id,
                'contest_title': contest.title,
                'round_id': submission.round_id,
                'user_id': user.id,
                'username': user.username,
                'title': submission.title,
                'status': submission.status,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                'ai': {
                    'flag_id': ai_flag.id,
                    'risk_level': ai_flag.risk_level,
                    'status': ai_flag.status,
                    'confidence_score': float(ai_flag.confidence_score) if ai_flag else None,
                } if ai_flag else None,
                'needs_review': True,
            })
        return items, total