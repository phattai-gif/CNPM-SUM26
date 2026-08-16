from infrastructure.databases.base import Base
from infrastructure.models import NotificationModel, ContestSettingsModel, SubmissionReviewModel


def test_app_models_are_exported_and_registered():
    assert NotificationModel.__tablename__ == "notifications"
    assert ContestSettingsModel.__tablename__ == "contest_settings"
    assert SubmissionReviewModel.__tablename__ == "submission_reviews"
    assert "app.notifications" in Base.metadata.tables
    assert "app.contest_settings" in Base.metadata.tables
    assert "app.submission_reviews" in Base.metadata.tables
