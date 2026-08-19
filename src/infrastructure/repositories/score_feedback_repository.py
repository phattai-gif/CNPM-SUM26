from typing import Optional
from sqlalchemy.orm import Session

try:
    from infrastructure.models.app import ScoreFeedbackModel
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory
except ImportError:
    from infrastructure.models.app import ScoreFeedbackModel
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory


class ScoreFeedbackRepository:
    def __init__(self, session: Optional[Session] = None):
        if session is not None:
            self.session = session
        else:
            try:
                self.session = db_factory.get_database('POSTGREE').session
            except Exception:
                from infrastructure.databases.postgres import session as pg_session
                self.session = pg_session

    def get_by_submission_judge(self, submission_id: int, judge_id: int) -> Optional[ScoreFeedbackModel]:
        return (
            self.session
            .query(ScoreFeedbackModel)
            .filter_by(submission_id=submission_id, judge_id=judge_id)
            .first()
        )

    def create_or_update(self, submission_id: int, judge_id: int, summary_feedback: str, final_recommendation: Optional[str] = None) -> ScoreFeedbackModel:
        try:
            model = self.get_by_submission_judge(submission_id, judge_id)
            if model is None:
                model = ScoreFeedbackModel(
                    submission_id=submission_id,
                    judge_id=judge_id,
                    summary_feedback=summary_feedback,
                    final_recommendation=final_recommendation,
                )
                self.session.add(model)
            else:
                model.summary_feedback = summary_feedback
                model.final_recommendation = final_recommendation

            self.session.commit()
            self.session.refresh(model)
            return model
        except Exception:
            self.session.rollback()
            raise

