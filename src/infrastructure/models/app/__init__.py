"""Canonical SQLAlchemy models for the application database.

This package contains the clean, schema-backed ORM definitions used to build
and maintain the database metadata. The file names use the app_ prefix to
separate them from legacy/incomplete model files in the parent package.
"""

from .app_user_model import UserModel
from .app_role_model import RoleModel, PermissionModel, user_roles, role_permissions
from .app_contest_model import ContestModel
from .app_announcement_model import ContestAnnouncementModel
from .app_round_model import RoundModel
from .app_criteria_model import CriteriaModel
from .app_submission_model import SubmissionModel
from .app_submission_file_model import SubmissionFileModel
from .app_submission_film_metadata_model import SubmissionFilmMetadataModel
from .app_judge_assignment_model import JudgeAssignmentModel
from .app_score_model import ScoreModel
from .app_score_feedback_model import ScoreFeedbackModel
from .app_ai_flag_model import AIFlagModel
from .app_ai_analysis_report_model import AIAnalysisReportModel
from .app_submission_ai_tag_model import SubmissionAITagModel
from .app_digital_archive_model import DigitalArchiveExhibitModel
from .app_audit_log_model import AuditLogModel
from .app_contest_settings_model import ContestSettingsModel
from .app_notification_model import NotificationModel
from .app_submission_review_model import SubmissionReviewModel

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
