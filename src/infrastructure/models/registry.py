"""Central ORM registry for application business modules.

This registry intentionally keeps a single source of truth for the core
business tables that participate in the user -> contest -> submission -> score -> AI workflow.
"""

from infrastructure.models.app import (
    AIAnalysisReportModel,
    AIFlagModel,
    ContestModel,
    CriteriaModel,
    JudgeAssignmentModel,
    RoleModel,
    RoundModel,
    ScoreModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
    SubmissionModel,
    UserModel,
    user_roles,
)

ORM_REGISTRY = {
    "UserModel": UserModel,
    "RoleModel": RoleModel,
    "user_roles": user_roles,
    "ContestModel": ContestModel,
    "RoundModel": RoundModel,
    "CriteriaModel": CriteriaModel,
    "SubmissionModel": SubmissionModel,
    "SubmissionFileModel": SubmissionFileModel,
    "SubmissionFilmMetadataModel": SubmissionFilmMetadataModel,
    "JudgeAssignmentModel": JudgeAssignmentModel,
    "ScoreModel": ScoreModel,
    "AIFlagModel": AIFlagModel,
    "AIAnalysisReportModel": AIAnalysisReportModel,
}

CORE_BIZ_REGISTRY = dict(ORM_REGISTRY)

__all__ = [
    "ORM_REGISTRY",
    "CORE_BIZ_REGISTRY",
    "UserModel",
    "RoleModel",
    "ContestModel",
    "RoundModel",
    "CriteriaModel",
    "SubmissionModel",
    "SubmissionFileModel",
    "SubmissionFilmMetadataModel",
    "JudgeAssignmentModel",
    "ScoreModel",
    "AIFlagModel",
    "AIAnalysisReportModel",
    "user_roles",
]
