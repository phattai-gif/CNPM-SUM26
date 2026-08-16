from infrastructure.repositories.notification_repository import NotificationRepository
from infrastructure.repositories.contest_settings_repository import ContestSettingsRepository
from infrastructure.repositories.submission_review_repository import SubmissionReviewRepository
from services.notification_service import NotificationService
from services.contest_settings_service import ContestSettingsService
from services.submission_review_service import SubmissionReviewService


def test_crud_services_and_repositories_are_available():
    assert hasattr(NotificationRepository, "create")
    assert hasattr(NotificationRepository, "get_by_id")
    assert hasattr(NotificationRepository, "list_by_user")
    assert hasattr(NotificationRepository, "mark_as_read")

    assert hasattr(ContestSettingsRepository, "get_by_contest_id")
    assert hasattr(ContestSettingsRepository, "create_or_update")

    assert hasattr(SubmissionReviewRepository, "create")
    assert hasattr(SubmissionReviewRepository, "get_by_submission")
    assert hasattr(SubmissionReviewRepository, "update_status")

    assert hasattr(NotificationService, "create_notification")
    assert hasattr(ContestSettingsService, "get_contest_settings")
    assert hasattr(SubmissionReviewService, "create_review")
