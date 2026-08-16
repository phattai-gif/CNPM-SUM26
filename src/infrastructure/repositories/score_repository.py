from typing import Optional, List
from sqlalchemy.orm import Session

try:
    from infrastructure.models.app import ScoreModel
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory
except ImportError:
    from infrastructure.models.app import ScoreModel
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory


class ScoreRepository:
    def __init__(self, session: Optional[Session] = None):
        if session is not None:
            self.session = session
        else:
            try:
                self.session = db_factory.get_database('POSTGREE').session
            except Exception:
                from infrastructure.databases.postgres import session as pg_session
                self.session = pg_session

    def get_by_submission_judge_criteria(self, submission_id: int, judge_id: int, criteria_id: int) -> Optional[ScoreModel]:
        return (
            self.session
            .query(ScoreModel)
            .filter_by(submission_id=submission_id, judge_id=judge_id, criteria_id=criteria_id)
            .first()
        )

    def create_or_update(self, submission_id: int, judge_id: int, criteria_id: int, score_value, comment: Optional[str] = None) -> ScoreModel:
        try:
            model = self.get_by_submission_judge_criteria(submission_id, judge_id, criteria_id)
            if model is None:
                model = ScoreModel(
                    submission_id=submission_id,
                    judge_id=judge_id,
                    criteria_id=criteria_id,
                    score_value=score_value,
                    comment=comment,
                )
                self.session.add(model)
            else:
                model.score_value = score_value
                model.comment = comment

            self.session.commit()
            self.session.refresh(model)
            return model
        except Exception:
            self.session.rollback()
            raise

    def list_by_submission(self, submission_id: int) -> List[ScoreModel]:
        return (
            self.session
            .query(ScoreModel)
            .filter_by(submission_id=submission_id)
            .all()
        )
