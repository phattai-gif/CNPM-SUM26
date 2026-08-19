#!/usr/bin/env python3
"""Database commands for initializing the schema and demo data.

Usage:
    python scripts/db.py init-schema
    python scripts/db.py seed
    python scripts/db.py init
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import insert, select
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "src" / ".env")

from config import FactoryConfig  # noqa: E402
from infrastructure.databases.factory_database import FactoryDatabase  # noqa: E402
from infrastructure.models.app import (  # noqa: E402
    AIAnalysisReportModel,
    AIFlagModel,
    ContestAnnouncementModel,
    ContestModel,
    ContestSettingsModel,
    CriteriaModel,
    JudgeAssignmentModel,
    RoundModel,
    ScoreFeedbackModel,
    ScoreModel,
    SubmissionFileModel,
    SubmissionFilmMetadataModel,
    SubmissionModel,
    UserModel,
    RoleModel,
    user_roles,
)


SCHEMA_FILE = ROOT / "src" / "migrations" / "schema.sql"
DEMO_PASSWORD = "Demo@12345"

ROLE_DATA = {
    "admin": ("Administrator", "Full access to the platform"),
    "organizer": ("Organizer", "Creates and manages contests"),
    "judge": ("Judge", "Reviews and scores submissions"),
    "participant": ("Participant", "Submits work to contests"),
}

USER_DATA = {
    "admin": ("demo_admin", "admin.demo@example.com", "Demo Administrator"),
    "organizer": ("demo_organizer", "organizer.demo@example.com", "Demo Organizer"),
    "judge": ("demo_judge", "judge.demo@example.com", "Demo Judge"),
    "participant": ("demo_participant", "participant.demo@example.com", "Demo Participant"),
}


def get_database():
    """Return the configured database without booting the Flask application."""
    if not FactoryConfig.get_config("development").DATABASE_URI:
        raise RuntimeError(
            "DATABASE_URI or POSTGREE_DATABASE_URL is required. "
            "Put it in .env or export it before running this command."
        )
    return FactoryDatabase.get_database("POSTGREE")


def init_schema() -> None:
    """Create all tables from the canonical PostgreSQL schema file."""
    database = get_database()
    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with database.engine.begin() as connection:
        connection.exec_driver_sql(schema_sql)
    print("Database schema initialized successfully.")


def _get_or_create_role(session, code: str) -> RoleModel:
    role = session.execute(select(RoleModel).where(RoleModel.code == code)).scalar_one_or_none()
    if role is None:
        name, description = ROLE_DATA[code]
        role = RoleModel(code=code, name=name, description=description)
        session.add(role)
        session.flush()
    return role


def _get_or_create_user(session, role: RoleModel, role_code: str) -> UserModel:
    username, email, full_name = USER_DATA[role_code]
    user = session.execute(select(UserModel).where(UserModel.username == username)).scalar_one_or_none()
    if user is None:
        user = UserModel(
            username=username,
            email=email,
            password_hash=generate_password_hash(DEMO_PASSWORD),
            full_name=full_name,
            status="active",
        )
        session.add(user)
        session.flush()

    linked = session.execute(
        select(user_roles).where(
            user_roles.c.user_id == user.id,
            user_roles.c.role_id == role.id,
        )
    ).first()
    if linked is None:
        session.execute(insert(user_roles).values(user_id=user.id, role_id=role.id))
    return user


def seed_demo_data() -> None:
    """Create repeatable demo records while preserving existing application data."""
    database = get_database()
    session = database.session
    try:
        roles = {code: _get_or_create_role(session, code) for code in ROLE_DATA}
        users = {
            code: _get_or_create_user(session, roles[code], code)
            for code in USER_DATA
        }

        contest = session.execute(
            select(ContestModel).where(ContestModel.slug == "demo-film-contest-2026")
        ).scalar_one_or_none()
        if contest is None:
            contest = ContestModel(
                title="Demo Film Photography Contest 2026",
                slug="demo-film-contest-2026",
                description="Demo contest for local development and end-to-end testing.",
                rules="Submit original film photography and include film metadata.",
                banner_url="https://images.unsplash.com/photo-1452780212940-6f5c0d14d848",
                created_by=users["organizer"].id,
                status="published",
            )
            session.add(contest)
            session.flush()

        settings = session.execute(
            select(ContestSettingsModel).where(ContestSettingsModel.contest_id == contest.id)
        ).scalar_one_or_none()
        if settings is None:
            session.add(ContestSettingsModel(
                contest_id=contest.id,
                allow_submission=True,
                max_submission_per_user=3,
                scoring_mode="weighted",
                judges_visible=True,
            ))

        announcement = session.execute(
            select(ContestAnnouncementModel).where(
                ContestAnnouncementModel.contest_id == contest.id,
                ContestAnnouncementModel.title == "Welcome to the demo contest",
            )
        ).scalar_one_or_none()
        if announcement is None:
            session.add(ContestAnnouncementModel(
                contest_id=contest.id,
                title="Welcome to the demo contest",
                content="This contest is ready for testing the organizer, judge, participant and AI workflows.",
                created_by=users["organizer"].id,
            ))

        round_obj = session.execute(
            select(RoundModel).where(
                RoundModel.contest_id == contest.id,
                RoundModel.round_number == 1,
            )
        ).scalar_one_or_none()
        if round_obj is None:
            round_obj = RoundModel(
                contest_id=contest.id,
                round_number=1,
                title="Open Submission",
                description="The demo round used by all local workflows.",
                weight=1.0,
                status="open",
            )
            session.add(round_obj)
            session.flush()

        criteria_data = [
            ("Composition", "Balance, framing and visual structure.", 10.0, 0.35),
            ("Technical Quality", "Exposure, focus, development and scan quality.", 10.0, 0.30),
            ("Storytelling", "Originality and emotional impact of the image.", 10.0, 0.35),
        ]
        criteria = []
        for name, description, max_score, weight in criteria_data:
            criterion = session.execute(
                select(CriteriaModel).where(
                    CriteriaModel.round_id == round_obj.id,
                    CriteriaModel.name == name,
                )
            ).scalar_one_or_none()
            if criterion is None:
                criterion = CriteriaModel(
                    round_id=round_obj.id,
                    name=name,
                    description=description,
                    max_score=max_score,
                    weight=weight,
                )
                session.add(criterion)
                session.flush()
            criteria.append(criterion)

        submission = session.execute(
            select(SubmissionModel).where(
                SubmissionModel.round_id == round_obj.id,
                SubmissionModel.user_id == users["participant"].id,
                SubmissionModel.title == "Morning Light",
            )
        ).scalar_one_or_none()
        if submission is None:
            submission = SubmissionModel(
                round_id=round_obj.id,
                user_id=users["participant"].id,
                title="Morning Light",
                story_description="A quiet morning captured on color negative film.",
                status="submitted",
                final_score=8.75,
            )
            submission.files.append(SubmissionFileModel(
                image_hd_url="https://images.unsplash.com/photo-1500534623283-312aade485b7",
                thumbnail_url="https://images.unsplash.com/photo-1500534623283-312aade485b7?w=640",
                width_px=1920,
                height_px=1280,
                file_hash="demo-morning-light-2026",
            ))
            submission.film_metadata = SubmissionFilmMetadataModel(
                film_stock="Kodak Portra 400",
                film_iso=400,
                camera_body="Nikon F3",
                lens="50mm f/1.8",
                lab_name="Demo Film Lab",
                development_process="C-41",
                taken_at_location="Hanoi, Vietnam",
            )
            session.add(submission)
            session.flush()

        assignment = session.execute(
            select(JudgeAssignmentModel).where(
                JudgeAssignmentModel.submission_id == submission.id,
                JudgeAssignmentModel.judge_id == users["judge"].id,
            )
        ).scalar_one_or_none()
        if assignment is None:
            session.add(JudgeAssignmentModel(
                round_id=round_obj.id,
                submission_id=submission.id,
                judge_id=users["judge"].id,
                status="assigned",
            ))

        for criterion, value in zip(criteria, (9.0, 8.5, 8.75)):
            score = session.execute(
                select(ScoreModel).where(
                    ScoreModel.submission_id == submission.id,
                    ScoreModel.judge_id == users["judge"].id,
                    ScoreModel.criteria_id == criterion.id,
                )
            ).scalar_one_or_none()
            if score is None:
                session.add(ScoreModel(
                    submission_id=submission.id,
                    judge_id=users["judge"].id,
                    criteria_id=criterion.id,
                    score_value=value,
                    comment="Strong demo score for UI and API testing.",
                ))

        feedback = session.execute(
            select(ScoreFeedbackModel).where(
                ScoreFeedbackModel.submission_id == submission.id,
                ScoreFeedbackModel.judge_id == users["judge"].id,
            )
        ).scalar_one_or_none()
        if feedback is None:
            session.add(ScoreFeedbackModel(
                submission_id=submission.id,
                judge_id=users["judge"].id,
                general_comment="A coherent and technically clean film photograph.",
                is_finalized=True,
                summary_feedback="Ready for the demo leaderboard.",
                final_recommendation="shortlist",
            ))

        ai_flag = session.execute(
            select(AIFlagModel).where(
                AIFlagModel.submission_id == submission.id,
                AIFlagModel.flag_type == "duplicate_similarity",
            )
        ).scalar_one_or_none()
        if ai_flag is None:
            ai_flag = AIFlagModel(
                submission_id=submission.id,
                flag_type="duplicate_similarity",
                confidence_score=0.08,
                risk_level="low",
                status="clear",
                review_notes="Demo record: no suspicious match detected.",
            )
            session.add(ai_flag)
            session.flush()
            session.add(AIAnalysisReportModel(
                submission_id=submission.id,
                ai_flag_id=ai_flag.id,
                ai_model_name="demo-detector-v1",
                ai_confidence_score=0.08,
                raw_details={"matches": [], "source": "seed"},
            ))

        session.commit()
        print("Demo data seeded successfully.")
        print(f"Demo password for all accounts: {DEMO_PASSWORD}")
        print(f"Contest slug: {contest.slug}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize schema and seed demo data.")
    parser.add_argument(
        "command",
        choices=("init-schema", "seed", "init"),
        help="init-schema creates tables; seed adds demo data; init runs both",
    )
    args = parser.parse_args()

    if args.command in ("init-schema", "init"):
        init_schema()
    if args.command in ("seed", "init"):
        seed_demo_data()


if __name__ == "__main__":
    main()