from infrastructure.databases.base import Base
from infrastructure.models import (
    AIAnalysisReportModel,
    AIFlagModel,
    ContestModel,
    CriteriaModel,
    RoleModel,
    RoundModel,
    ScoreModel,
    SubmissionModel,
    UserModel,
    ORM_REGISTRY,
)


def test_business_orm_registry_contains_core_tables():
    expected_tables = {
        "app.users",
        "app.roles",
        "app.contests",
        "app.rounds",
        "app.criteria",
        "app.submissions",
        "app.scores",
        "app.ai_flags",
        "app.ai_analysis_reports",
    }

    assert ORM_REGISTRY
    assert set(ORM_REGISTRY.keys()) >= {
        "UserModel",
        "RoleModel",
        "ContestModel",
        "RoundModel",
        "CriteriaModel",
        "SubmissionModel",
        "ScoreModel",
        "AIFlagModel",
        "AIAnalysisReportModel",
    }
    assert set(Base.metadata.tables.keys()) >= expected_tables

    for model in (
        UserModel,
        RoleModel,
        ContestModel,
        RoundModel,
        CriteriaModel,
        SubmissionModel,
        ScoreModel,
        AIFlagModel,
        AIAnalysisReportModel,
    ):
        assert model.__table__.schema == "app"
        assert model.__table__.name in {
            "users",
            "roles",
            "contests",
            "rounds",
            "criteria",
            "submissions",
            "scores",
            "ai_flags",
            "ai_analysis_reports",
        }


def test_business_models_define_relationships_for_core_flow():
    assert hasattr(UserModel, "contests")
    assert hasattr(UserModel, "submissions")
    assert hasattr(ContestModel, "rounds")
    assert hasattr(RoundModel, "criteria")
    assert hasattr(RoundModel, "submissions")
    assert hasattr(SubmissionModel, "scores")
    assert hasattr(SubmissionModel, "ai_flags")
    assert hasattr(SubmissionModel, "film_metadata")
    assert hasattr(ScoreModel, "submission")
    assert hasattr(AIFlagModel, "analysis_report")
