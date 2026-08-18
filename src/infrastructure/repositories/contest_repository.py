from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

try:
    from domain.models.icontest_repository import IContestRepository
    from domain.contest import Contest, Round, Criteria
    from infrastructure.models.app import ContestModel, RoundModel, CriteriaModel
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory
except ImportError:
    from domain.models.icontest_repository import IContestRepository
    from domain.contest import Contest, Round, Criteria
    from infrastructure.models.app import ContestModel, RoundModel, CriteriaModel
    from infrastructure.databases.factory_database import FactoryDatabase as db_factory


class ContestRepository(IContestRepository):
    def __init__(self, session: Optional[Session] = None):
        if session is not None:
            self.session = session
        else:
            try:
                self.session = db_factory.get_database('POSTGREE').session
            except Exception:
                from infrastructure.databases.postgres import session as pg_session
                self.session = pg_session

    def _rollback_session(self):
        try:
            self.session.rollback()
        except Exception:
            pass

    def _to_domain_criteria(self, model: CriteriaModel) -> Criteria:
        if not model:
            return None
        return Criteria(
            id=model.id,
            round_id=model.round_id,
            name=model.name,
            description=model.description,
            max_score=float(model.max_score) if model.max_score is not None else 10.0,
            weight=float(model.weight) if model.weight is not None else 1.0,
            created_at=model.created_at
        )

    def _to_domain_round(self, model: RoundModel) -> Round:
        if not model:
            return None
        criteria_list = []
        try:
            criteria_models = self.session.query(CriteriaModel).filter_by(round_id=model.id).all()
            criteria_list = [self._to_domain_criteria(c) for c in criteria_models]
        except Exception:
            self._rollback_session()

        return Round(
            id=model.id,
            contest_id=model.contest_id,
            round_number=model.round_number,
            title=model.title,
            description=model.description,
            start_date=model.start_date,
            end_date=model.end_date,
            weight=float(model.weight) if model.weight is not None else 1.0,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            criteria=criteria_list
        )

    def _to_domain_contest(self, model: ContestModel) -> Contest:
        if not model:
            return None
        rounds_list = []
        try:
            round_models = self.session.query(RoundModel).filter_by(contest_id=model.id).order_by(RoundModel.round_number.asc()).all()
            rounds_list = [self._to_domain_round(r) for r in round_models]
        except Exception:
            self._rollback_session()

        return Contest(
            id=model.id,
            title=model.title,
            slug=model.slug,
            description=model.description,
            rules=getattr(model, 'rules', None),
            banner_url=model.banner_url,
            created_by=model.created_by,
            status=model.status,
            start_date=model.start_date,
            end_date=model.end_date,
            created_at=model.created_at,
            updated_at=model.updated_at,
            rounds=rounds_list
        )

    def create_contest(self, contest: Contest) -> Contest:
        try:
            self._rollback_session()
            model = ContestModel(
                title=contest.title,
                slug=contest.slug,
                description=contest.description,
                rules=contest.rules,
                banner_url=contest.banner_url,
                created_by=contest.created_by,
                status=contest.status or 'draft',
                start_date=contest.start_date,
                end_date=contest.end_date
            )
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_domain_contest(model)
        except Exception as e:
            self._rollback_session()
            raise e

    def get_contest_by_id(self, contest_id: int) -> Optional[Contest]:
        try:
            self._rollback_session()
            model = self.session.query(ContestModel).filter_by(id=contest_id).first()
            if not model:
                return None
            return self._to_domain_contest(model)
        except Exception as e:
            self._rollback_session()
            return None

    def get_contests_by_organizer(self, created_by: int) -> List[Contest]:
        try:
            self._rollback_session()
            models = self.session.query(ContestModel).filter_by(created_by=created_by).order_by(ContestModel.created_at.desc()).all()
            return [self._to_domain_contest(m) for m in models]
        except Exception:
            self._rollback_session()
            return []

    def update_contest(self, contest_id: int, data: dict) -> Optional[Contest]:
        try:
            self._rollback_session()
            model = self.session.query(ContestModel).filter_by(id=contest_id).first()
            if not model:
                return None
            for key, value in data.items():
                if hasattr(model, key) and key not in ('id', 'created_by', 'created_at'):
                    setattr(model, key, value)
            self.session.commit()
            self.session.refresh(model)
            return self._to_domain_contest(model)
        except Exception as e:
            self._rollback_session()
            raise e

    def update_rules(self, contest_id: int, rules: str) -> Optional[Contest]:
        return self.update_contest(contest_id, {'rules': rules})

    def delete_contest(self, contest_id: int) -> bool:
        try:
            self._rollback_session()
            model = self.session.query(ContestModel).filter_by(id=contest_id).first()
            if not model:
                return False
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            self._rollback_session()
            raise e

    def create_round(self, round_obj: Round) -> Round:
        try:
            self._rollback_session()
            model = RoundModel(
                contest_id=round_obj.contest_id,
                round_number=round_obj.round_number,
                title=round_obj.title,
                description=round_obj.description,
                start_date=round_obj.start_date,
                end_date=round_obj.end_date,
                weight=round_obj.weight,
                status=round_obj.status or 'upcoming'
            )
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)

            if round_obj.criteria:
                for c in round_obj.criteria:
                    crit_model = CriteriaModel(
                        round_id=model.id,
                        name=c.name,
                        description=c.description,
                        max_score=c.max_score,
                        weight=c.weight
                    )
                    self.session.add(crit_model)
                self.session.commit()

            return self._to_domain_round(model)
        except Exception as e:
            self._rollback_session()
            raise e

    def get_round_by_id(self, round_id: int) -> Optional[Round]:
        try:
            self._rollback_session()
            model = self.session.query(RoundModel).filter_by(id=round_id).first()
            if not model:
                return None
            return self._to_domain_round(model)
        except Exception:
            self._rollback_session()
            return None

    def get_rounds_by_contest_id(self, contest_id: int) -> List[Round]:
        try:
            self._rollback_session()
            models = self.session.query(RoundModel).filter_by(contest_id=contest_id).order_by(RoundModel.round_number.asc()).all()
            return [self._to_domain_round(m) for m in models]
        except Exception:
            self._rollback_session()
            return []

    def update_round(self, round_id: int, data: dict) -> Optional[Round]:
        try:
            self._rollback_session()
            model = self.session.query(RoundModel).filter_by(id=round_id).first()
            if not model:
                return None
            for key, value in data.items():
                if hasattr(model, key) and key not in ('id', 'contest_id', 'created_at'):
                    setattr(model, key, value)
            self.session.commit()
            self.session.refresh(model)
            return self._to_domain_round(model)
        except Exception as e:
            self._rollback_session()
            raise e

    def delete_round(self, round_id: int) -> bool:
        try:
            self._rollback_session()
            model = self.session.query(RoundModel).filter_by(id=round_id).first()
            if not model:
                return False
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            self._rollback_session()
            raise e

    def create_criteria(self, criteria_obj: Criteria) -> Criteria:
        try:
            self._rollback_session()
            model = CriteriaModel(
                round_id=criteria_obj.round_id,
                name=criteria_obj.name,
                description=criteria_obj.description,
                max_score=criteria_obj.max_score,
                weight=criteria_obj.weight
            )
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_domain_criteria(model)
        except Exception as e:
            self._rollback_session()
            raise e

    def get_criteria_by_id(self, criteria_id: int) -> Optional[Criteria]:
        try:
            self._rollback_session()
            model = self.session.query(CriteriaModel).filter_by(id=criteria_id).first()
            if not model:
                return None
            return self._to_domain_criteria(model)
        except Exception:
            self._rollback_session()
            return None

    def get_criteria_by_round_id(self, round_id: int) -> List[Criteria]:
        try:
            self._rollback_session()
            models = self.session.query(CriteriaModel).filter_by(round_id=round_id).all()
            return [self._to_domain_criteria(m) for m in models]
        except Exception:
            self._rollback_session()
            return []

    def update_criteria(self, criteria_id: int, data: dict) -> Optional[Criteria]:
        try:
            self._rollback_session()
            model = self.session.query(CriteriaModel).filter_by(id=criteria_id).first()
            if not model:
                return None
            for key, value in data.items():
                if hasattr(model, key) and key not in ('id', 'round_id', 'created_at'):
                    setattr(model, key, value)
            self.session.commit()
            self.session.refresh(model)
            return self._to_domain_criteria(model)
        except Exception as e:
            self._rollback_session()
            raise e

    def delete_criteria(self, criteria_id: int) -> bool:
        try:
            self._rollback_session()
            model = self.session.query(CriteriaModel).filter_by(id=criteria_id).first()
            if not model:
                return False
            self.session.delete(model)
            self.session.commit()
            return True
        except Exception as e:
            self._rollback_session()
            raise e

    def update_contest_configuration(self, contest_id: int, rules: Optional[str], rounds_data: List[dict]) -> Optional[Contest]:
        try:
            self._rollback_session()
            contest_model = self.session.query(ContestModel).filter_by(id=contest_id).first()
            if not contest_model:
                return None

            if rules is not None:
                contest_model.rules = rules

            if rounds_data is not None:
                existing_rounds = self.session.query(RoundModel).filter_by(contest_id=contest_id).all()
                for r in existing_rounds:
                    self.session.query(CriteriaModel).filter_by(round_id=r.id).delete()
                    self.session.delete(r)
                self.session.flush()

                for index, r_data in enumerate(rounds_data, start=1):
                    start_dt = r_data.get('start_date')
                    end_dt = r_data.get('end_date')
                    if isinstance(start_dt, str):
                        try: start_dt = datetime.fromisoformat(start_dt)
                        except Exception: start_dt = None
                    if isinstance(end_dt, str):
                        try: end_dt = datetime.fromisoformat(end_dt)
                        except Exception: end_dt = None

                    round_model = RoundModel(
                        contest_id=contest_id,
                        round_number=r_data.get('round_number', index),
                        title=r_data.get('title', f"Vong {index}"),
                        description=r_data.get('description'),
                        start_date=start_dt,
                        end_date=end_dt,
                        weight=r_data.get('weight', 1.0),
                        status=r_data.get('status', 'upcoming')
                    )
                    self.session.add(round_model)
                    self.session.flush()

                    criteria_list = r_data.get('criteria', [])
                    for c_data in criteria_list:
                        crit_model = CriteriaModel(
                            round_id=round_model.id,
                            name=c_data.get('name', ''),
                            description=c_data.get('description'),
                            max_score=c_data.get('max_score', 10.0),
                            weight=c_data.get('weight', 1.0)
                        )
                        self.session.add(crit_model)

            self.session.commit()
            return self.get_contest_by_id(contest_id)
        except Exception as e:
            self._rollback_session()
            raise e

