from datetime import datetime, timezone

from sqlalchemy import distinct, func, select

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import (
    AIAnalysisReportModel,
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
            reason = None
            warning_type = None
            if ai_flag:
                warning_type = ai_flag.flag_type
                reason = ai_flag.review_notes

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
                    'warning_type': warning_type,
                    'risk_level': ai_flag.risk_level,
                    'status': ai_flag.status,
                    'confidence_score': float(ai_flag.confidence_score) if ai_flag else None,
                    'reason': reason,
                } if ai_flag else None,
                'needs_review': True,
            })
        return items, total

    def get_submission_ai_report(self, contest_ids, submission_id):
        latest_flag_id = (
            select(func.max(AIFlagModel.id))
            .where(AIFlagModel.submission_id == SubmissionModel.id)
            .correlate(SubmissionModel)
            .scalar_subquery()
        )
        row = (
            self.session.query(
                SubmissionModel,
                ContestModel,
                UserModel,
                AIFlagModel,
                AIAnalysisReportModel,
            )
            .join(RoundModel, SubmissionModel.round_id == RoundModel.id)
            .join(ContestModel, RoundModel.contest_id == ContestModel.id)
            .join(UserModel, SubmissionModel.user_id == UserModel.id)
            .outerjoin(AIFlagModel, AIFlagModel.id == latest_flag_id)
            .outerjoin(
                AIAnalysisReportModel,
                AIAnalysisReportModel.ai_flag_id == AIFlagModel.id,
            )
            .filter(ContestModel.id.in_(contest_ids))
            .filter(SubmissionModel.id == submission_id)
            .first()
        )

        if not row:
            return None

        submission, contest, user, ai_flag, report = row
        reason = None
        report_details = None
        similarity_submission_id = None

        if report:
            report_details = report.raw_details
            similarity_submission_id = report.similarity_matched_submission_id
            if isinstance(report.raw_details, dict):
                reason = report.raw_details.get('reason') or report.raw_details.get('summary')

        if not reason and ai_flag:
            reason = ai_flag.review_notes

        return {
            'submission': {
                'id': submission.id,
                'title': submission.title,
                'status': submission.status,
                'contest_id': contest.id,
                'contest_title': contest.title,
                'author': {
                    'id': user.id,
                    'username': user.username,
                },
            },
            'ai_flag': {
                'id': ai_flag.id if ai_flag else None,
                'warning_type': ai_flag.flag_type if ai_flag else None,
                'confidence_score': float(ai_flag.confidence_score) if ai_flag else None,
                'risk_level': ai_flag.risk_level if ai_flag else None,
                'status': ai_flag.status if ai_flag else None,
                'reason': reason,
                'review_notes': ai_flag.review_notes if ai_flag else None,
                'reviewed_at': ai_flag.reviewed_at.isoformat() if ai_flag and ai_flag.reviewed_at else None,
            },
            'ai_report': {
                'id': report.id if report else None,
                'model': report.ai_model_name if report else None,
                'confidence_score': float(report.ai_confidence_score) if report and report.ai_confidence_score is not None else None,
                'similarity_matched_submission_id': similarity_submission_id,
                'created_at': report.created_at.isoformat() if report and report.created_at else None,
                'raw_details': report_details,
            },
        }

    def moderate_submission(self, contest_ids, submission_id, action, reviewer_id, review_notes=None):
        latest_flag_id = (
            select(func.max(AIFlagModel.id))
            .where(AIFlagModel.submission_id == SubmissionModel.id)
            .correlate(SubmissionModel)
            .scalar_subquery()
        )

        row = (
            self.session.query(SubmissionModel, AIFlagModel)
            .join(RoundModel, SubmissionModel.round_id == RoundModel.id)
            .join(ContestModel, RoundModel.contest_id == ContestModel.id)
            .outerjoin(AIFlagModel, AIFlagModel.id == latest_flag_id)
            .filter(ContestModel.id.in_(contest_ids))
            .filter(SubmissionModel.id == submission_id)
            .first()
        )

        if not row:
            return None

        submission, ai_flag = row
        now_utc = datetime.now(timezone.utc)

        if action == 'approve':
            submission.status = 'submitted'
            if ai_flag:
                ai_flag.status = 'approved'
        elif action == 'reject':
            submission.status = 'rejected'
            if ai_flag:
                ai_flag.status = 'rejected'
        elif action == 'dismiss-flag':
            submission.status = 'submitted'
            if ai_flag:
                ai_flag.status = 'dismissed'
        else:
            raise ValueError('Unsupported moderation action')

        if ai_flag:
            ai_flag.reviewed_by = reviewer_id
            ai_flag.reviewed_at = now_utc
            if review_notes is not None:
                ai_flag.review_notes = review_notes

        self.session.commit()

        # Refresh objects to ensure we return values reflecting the persisted DB state
        try:
            self.session.refresh(submission)
        except Exception:
            # ignore refresh errors, continue to construct response
            pass

        if ai_flag:
            try:
                self.session.refresh(ai_flag)
            except Exception:
                pass

        return {
            'submission_id': submission.id,
            'submission_status': submission.status,
            'ai_flag_id': ai_flag.id if ai_flag else None,
            'ai_flag_status': ai_flag.status if ai_flag else None,
            'reviewed_at': now_utc.isoformat(),
        }