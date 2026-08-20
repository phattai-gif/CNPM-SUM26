from typing import Optional, List
from sqlalchemy.orm import Session

from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import NotificationModel


class NotificationRepository:
    def __init__(self, session: Optional[Session] = None):
        if session is not None:
            self.session = session
        else:
            self.session = db_factory.get_database('POSTGREE').session

    def create(self, user_id: int, title: str, body: Optional[str] = None,
               contest_id: Optional[int] = None, notification_type: str = 'info') -> NotificationModel:
        model = NotificationModel(
            user_id=user_id,
            contest_id=contest_id,
            title=title,
            body=body,
            notification_type=notification_type,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model

    def get_by_id(self, notification_id: int) -> Optional[NotificationModel]:
        return self.session.query(NotificationModel).filter_by(id=notification_id).first()

    def list_by_user(self, user_id: int, unread_only: bool = False) -> List[NotificationModel]:
        query = self.session.query(NotificationModel).filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        return query.order_by(NotificationModel.created_at.desc()).all()

    def mark_as_read(self, notification_id: int) -> Optional[NotificationModel]:
        model = self.get_by_id(notification_id)
        if model is None:
            return None
        model.is_read = True
        self.session.commit()
        self.session.refresh(model)
        return model

