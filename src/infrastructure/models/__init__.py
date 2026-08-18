"""Clean SQLAlchemy model exports for the application database.

Only the canonical app-prefixed models are re-exported here to avoid duplicate
ORM metadata registration from legacy model files in the parent package.
"""

from .app import *  # noqa: F401,F403

__all__ = [
    "UserModel",
    "RoleModel",
    "PermissionModel",
    "user_roles",
    "role_permissions",
    "ContestModel",
    "ContestAnnouncementModel",
    "RoundModel",
    "CriteriaModel",
    "SubmissionModel",
    "SubmissionFileModel",
    "SubmissionFilmMetadataModel",
    "JudgeAssignmentModel",
    "ScoreModel",
    "ScoreFeedbackModel",
    "AIFlagModel",
    "AIAnalysisReportModel",
    "SubmissionAITagModel",
    "DigitalArchiveExhibitModel",
    "AuditLogModel",
    "ContestSettingsModel",
    "NotificationModel",
    "SubmissionReviewModel",
] 
