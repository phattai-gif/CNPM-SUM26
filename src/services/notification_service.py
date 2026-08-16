from typing import Optional, List

from infrastructure.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, repository: Optional[NotificationRepository] = None):
        self.repository = repository or NotificationRepository()

    def create_notification(self, user_id: int, title: str, body: Optional[str] = None,
                           contest_id: Optional[int] = None, notification_type: str = 'info'):
        return self.repository.create(
            user_id=user_id,
            title=title,
            body=body,
            contest_id=contest_id,
            notification_type=notification_type,
        )

    def get_user_notifications(self, user_id: int, unread_only: bool = False) -> List:
        return self.repository.list_by_user(user_id=user_id, unread_only=unread_only)

    def mark_notification_read(self, notification_id: int):
        return self.repository.mark_as_read(notification_id)
