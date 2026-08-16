from typing import Optional
from sqlalchemy.orm import Session

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import ContestSettingsModel


class ContestSettingsRepository:
    def __init__(self, session: Optional[Session] = None):
        if session is not None:
            self.session = session
        else:
            self.session = db_factory.get_database('POSTGREE').session

    def get_by_contest_id(self, contest_id: int) -> Optional[ContestSettingsModel]:
        return self.session.query(ContestSettingsModel).filter_by(contest_id=contest_id).first()

    def create_or_update(self, contest_id: int, **kwargs) -> ContestSettingsModel:
        model = self.get_by_contest_id(contest_id)
        if model is None:
            model = ContestSettingsModel(contest_id=contest_id)
            self.session.add(model)

        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)

        self.session.commit()
        self.session.refresh(model)
        return model
