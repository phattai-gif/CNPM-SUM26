import os
import sys
import jwt
import pytest
from datetime import datetime, timezone

os.environ["TESTING"] = "True"
os.environ["POSTGREE_DATABASE_URL"] = "sqlite:///:memory:"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from config import Config
from create_app import create_app
from infrastructure.databases.factory_database import FactoryDatabase
from infrastructure.databases.base import Base
from infrastructure.models.app import (
    ContestModel,
    RoundModel,
    SubmissionModel,
    SubmissionReviewModel,
    UserModel,
)


@pytest.fixture
def app():
    app_instance = create_app()
    return app_instance


@pytest.fixture
def client(app):
    return app.test_client()


def create_jwt_token(user_id, username="testuser", role="participant"):
    secret_key = Config.SECRET_KEY or "dev-secret-key-change-me-in-production-32chars"
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


@pytest.fixture
def db_session(app):
    db = FactoryDatabase.get_database("POSTGREE")
    # Ensure tables exist for sqlite in-memory DB
    try:
        Base.metadata.create_all(db.engine)
    except Exception:
        pass
    return db.session


@pytest.fixture
def setup_test_data(db_session):
    db_session.query(SubmissionReviewModel).delete()
    db_session.query(SubmissionModel).delete()
    db_session.query(RoundModel).delete()
    db_session.query(ContestModel).delete()
    db_session.query(UserModel).delete()
    db_session.commit()

    # Create Users
    winner_user = UserModel(
        username="winner_user",
        email="winner@example.com",
        password_hash="hashed_pw",
        full_name="Nguyen Van A",
        status="active",
    )
    other_user = UserModel(
        username="other_user",
        email="other@example.com",
        password_hash="hashed_pw",
        full_name="Tran Van B",
        status="active",
    )
    db_session.add_all([winner_user, other_user])
    db_session.commit()

    # Create Contest & Round
    contest = ContestModel(
        title="Summer Film Contest 2026",
        slug="summer-film-contest-2026",
        description="Annual film photography contest",
        created_by=winner_user.id,
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

    # Create Submissions
    approved_winner_sub = SubmissionModel(
        round_id=round_obj.id,
        user_id=winner_user.id,
        title="Sunset over Old Town",
        status="approved",
        final_score=98.5,
    )

    unapproved_winner_user = UserModel(
        username="unapproved_winner",
        email="unapproved@example.com",
        password_hash="hashed_pw",
        full_name="Le Van C",
        status="active",
    )
    db_session.add(unapproved_winner_user)
    db_session.commit()

    unapproved_winner_sub = SubmissionModel(
        round_id=round_obj.id,
        user_id=unapproved_winner_user.id,
        title="Morning Harbor",
        status="submitted",
        final_score=95.0,
    )

    non_winner_sub = SubmissionModel(
        round_id=round_obj.id,
        user_id=other_user.id,
        title="City Night",
        status="approved",
        final_score=60.0,
    )

    db_session.add_all([approved_winner_sub, unapproved_winner_sub, non_winner_sub])
    db_session.commit()

    return {
        "winner_user": winner_user,
        "other_user": other_user,
        "unapproved_winner_user": unapproved_winner_user,
        "contest": contest,
        "round": round_obj,
        "approved_winner_sub": approved_winner_sub,
        "unapproved_winner_sub": unapproved_winner_sub,
        "non_winner_sub": non_winner_sub,
    }


def test_case_1_get_certificate_approved_winner(client, setup_test_data):
    data = setup_test_data
    sub_id = data["approved_winner_sub"].id
    user_id = data["winner_user"].id
    token = create_jwt_token(user_id=user_id, username="winner_user")

    res = client.get(
        f"/api/certificates/{sub_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    cert_info = json_data["data"]
    assert cert_info["winner"]["name"] == "Nguyen Van A"
    assert cert_info["contest"]["name"] == "Summer Film Contest 2026"
    assert cert_info["award"]["name"] == "First Prize"
    assert "download" in cert_info["certificate_url"]


def test_case_2_get_certificate_not_winner(client, setup_test_data):
    data = setup_test_data
    sub_id = data["non_winner_sub"].id
    user_id = data["other_user"].id
    token = create_jwt_token(user_id=user_id, username="other_user")

    res = client.get(
        f"/api/certificates/{sub_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "Certificate is not available" in json_data["message"]


def test_case_3_get_certificate_winner_not_approved(client, setup_test_data):
    data = setup_test_data
    sub_id = data["unapproved_winner_sub"].id
    user_id = data["unapproved_winner_user"].id
    token = create_jwt_token(user_id=user_id, username="unapproved_winner")

    res = client.get(
        f"/api/certificates/{sub_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "has not been approved yet" in json_data["message"]


def test_case_4_download_certificate_pdf(client, setup_test_data):
    data = setup_test_data
    sub_id = data["approved_winner_sub"].id
    user_id = data["winner_user"].id
    token = create_jwt_token(user_id=user_id, username="winner_user")

    res = client.get(
        f"/api/certificates/{sub_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert "attachment" in res.headers.get("Content-Disposition", "")
    assert len(res.data) > 0


def test_case_5_social_sharing_metadata(client, setup_test_data):
    data = setup_test_data
    sub_id = data["approved_winner_sub"].id

    res = client.get(f"/api/certificates/{sub_id}/share")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["success"] is True
    meta = json_data["data"]
    assert "Nguyen Van A" in meta["title"]
    assert "First Prize" in meta["title"]
    assert "Summer Film Contest 2026" in meta["description"]
    assert "image" in meta
    assert "url" in meta


def test_case_6_unauthorized_access(client, setup_test_data):
    data = setup_test_data
    sub_id = data["approved_winner_sub"].id
    other_user_id = data["other_user"].id

    # 1. No token -> 401
    res1 = client.get(f"/api/certificates/{sub_id}")
    assert res1.status_code == 401

    # 2. Token from another participant -> 403
    other_token = create_jwt_token(user_id=other_user_id, username="other_user")
    res2 = client.get(
        f"/api/certificates/{sub_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res2.status_code == 403


def test_case_7_certificate_not_found(client, setup_test_data):
    token = create_jwt_token(user_id=9999, username="random_user")

    res = client.get(
        "/api/certificates/999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "not found" in json_data["message"].lower()
