import os
import sys

import jwt
import pytest

os.environ["TESTING"] = "True"
os.environ["POSTGREE_DATABASE_URL"] = "sqlite:///:memory:"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from config import Config
from create_app import create_app
from infrastructure.databases.factory_database import FactoryDatabase
from infrastructure.databases.base import Base
from infrastructure.models.app import ContestModel, RoundModel, SubmissionModel, UserModel, DigitalArchiveExhibitModel


@pytest.fixture
def app():
    app_instance = create_app()
    return app_instance


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    db = FactoryDatabase.get_database("POSTGREE")
    try:
        Base.metadata.create_all(db.engine)
    except Exception:
        pass
    return db.session


def create_jwt_token(user_id, username="organizer", role="organizer"):
    secret_key = Config.SECRET_KEY or "dev-secret-key-change-me-in-production-32chars"
    payload = {"user_id": user_id, "username": username, "role": role}
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


@pytest.fixture
def organizer_contest_data(db_session):
    db_session.query(DigitalArchiveExhibitModel).delete()
    db_session.query(SubmissionModel).delete()
    db_session.query(RoundModel).delete()
    db_session.query(ContestModel).delete()
    db_session.query(UserModel).delete()
    db_session.commit()

    organizer = UserModel(
        username="organizer_user",
        email="organizer@example.com",
        password_hash="hashed_pw",
        full_name="Organizer User",
        status="active",
    )
    participant = UserModel(
        username="participant_user",
        email="participant@example.com",
        password_hash="hashed_pw",
        full_name="Participant User",
        status="active",
    )
    db_session.add_all([organizer, participant])
    db_session.commit()

    contest = ContestModel(
        title="Spring Photo Contest",
        slug="spring-photo-contest",
        description="Spring contest",
        created_by=organizer.id,
        status="active",
        awards_json=[
            {"rank": 1, "name": "First Prize"},
            {"rank": 2, "name": "Second Prize"},
        ],
    )
    db_session.add(contest)
    db_session.commit()

    round_obj = RoundModel(
        contest_id=contest.id,
        round_number=1,
        title="Final Round",
        status="FINALIZED",
    )
    db_session.add(round_obj)
    db_session.commit()

    first_place = SubmissionModel(
        round_id=round_obj.id,
        user_id=participant.id,
        title="First Place Shot",
        status="submitted",
        final_score=98.5,
    )
    second_place = SubmissionModel(
        round_id=round_obj.id,
        user_id=participant.id,
        title="Second Place Shot",
        status="submitted",
        final_score=93.5,
    )
    db_session.add_all([first_place, second_place])
    db_session.commit()

    return {
        "organizer": organizer,
        "participant": participant,
        "contest": contest,
        "round": round_obj,
        "first_place": first_place,
        "second_place": second_place,
    }


def test_organizer_can_list_winner_candidates(client, organizer_contest_data):
    contest = organizer_contest_data["contest"]
    round_obj = organizer_contest_data["round"]
    first_place_id = organizer_contest_data["first_place"].id
    token = create_jwt_token(organizer_contest_data["organizer"].id, username="organizer_user", role="organizer")

    response = client.get(
        f"/organizer/contests/{contest.id}/rounds/{round_obj.id}/winners",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["contest_id"] == contest.id
    assert payload["round_id"] == round_obj.id
    assert len(payload["winner_candidates"]) >= 2
    assert payload["winner_candidates"][0]["submission_id"] == first_place_id
    assert payload["winner_candidates"][0]["final_score"] == 98.5


def test_organizer_can_approve_and_reject_winner(client, organizer_contest_data):
    contest = organizer_contest_data["contest"]
    round_obj = organizer_contest_data["round"]
    first_place = organizer_contest_data["first_place"]
    token = create_jwt_token(organizer_contest_data["organizer"].id, username="organizer_user", role="organizer")

    approve_response = client.patch(
        f"/organizer/contests/{contest.id}/rounds/{round_obj.id}/winners/{first_place.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "approve", "award_title": "First Prize"},
    )

    assert approve_response.status_code == 200
    approve_payload = approve_response.get_json()
    assert approve_payload["success"] is True
    assert approve_payload["decision"] == "approve"
    assert approve_payload["submission"]["status"] == "winner"
    assert approve_payload["archive"]["award_title"] == "First Prize"

    db = FactoryDatabase.get_database("POSTGREE")
    saved_submission = db.session.query(SubmissionModel).filter_by(id=first_place.id).first()
    archive_record = db.session.query(DigitalArchiveExhibitModel).filter_by(submission_id=first_place.id).first()
    assert saved_submission.status == "winner"
    assert archive_record is not None
    assert archive_record.award_title == "First Prize"

    reject_response = client.patch(
        f"/organizer/contests/{contest.id}/rounds/{round_obj.id}/winners/{first_place.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "reject", "reason": "Not compliant with rules"},
    )

    assert reject_response.status_code == 200
    reject_payload = reject_response.get_json()
    assert reject_payload["success"] is True
    assert reject_payload["decision"] == "reject"
    assert reject_payload["submission"]["status"] == "rejected"
    assert reject_payload["archive"] is None

    updated_submission = db.session.query(SubmissionModel).filter_by(id=first_place.id).first()
    assert updated_submission.status == "rejected"
    assert db.session.query(DigitalArchiveExhibitModel).filter_by(submission_id=first_place.id).count() == 0
