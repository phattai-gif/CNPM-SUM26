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
from infrastructure.models.app import (
    ContestModel,
    RoundModel,
    SubmissionModel,
    UserModel,
    VoteModel,
    DigitalArchiveExhibitModel,
)


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


def create_jwt_token(user_id, username="user", role="participant"):
    secret_key = Config.SECRET_KEY or "dev-secret-key-change-me-in-production-32chars"
    payload = {"user_id": user_id, "username": username, "role": role}
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


@pytest.fixture
def vote_test_data(db_session):
    """Create test data for voting: organizer, participants, contest, round, and winner submissions."""
    db_session.query(VoteModel).delete()
    db_session.query(DigitalArchiveExhibitModel).delete()
    db_session.query(SubmissionModel).delete()
    db_session.query(RoundModel).delete()
    db_session.query(ContestModel).delete()
    db_session.query(UserModel).delete()
    db_session.commit()

    # Create users
    organizer = UserModel(
        username="organizer_vote_test",
        email="organizer_vote@example.com",
        password_hash="hashed_pw",
        full_name="Organizer",
        status="active",
    )
    voter1 = UserModel(
        username="voter1",
        email="voter1@example.com",
        password_hash="hashed_pw",
        full_name="Voter 1",
        status="active",
    )
    voter2 = UserModel(
        username="voter2",
        email="voter2@example.com",
        password_hash="hashed_pw",
        full_name="Voter 2",
        status="active",
    )
    photographer1 = UserModel(
        username="photographer1",
        email="photo1@example.com",
        password_hash="hashed_pw",
        full_name="Photographer 1",
        status="active",
    )
    photographer2 = UserModel(
        username="photographer2",
        email="photo2@example.com",
        password_hash="hashed_pw",
        full_name="Photographer 2",
        status="active",
    )
    db_session.add_all([organizer, voter1, voter2, photographer1, photographer2])
    db_session.commit()

    # Create contest and round
    contest = ContestModel(
        title="Voting Test Contest",
        slug="voting-test-contest",
        description="Contest for voting tests",
        created_by=organizer.id,
        status="active",
    )
    db_session.add(contest)
    db_session.commit()

    round_obj = RoundModel(
        contest_id=contest.id,
        round_number=1,
        title="Voting Round",
        status="FINALIZED",
    )
    db_session.add(round_obj)
    db_session.commit()

    # Create submissions: winner and non-winner
    winner_submission = SubmissionModel(
        round_id=round_obj.id,
        user_id=photographer1.id,
        title="Beautiful Sunset - WINNER",
        status="winner",  # This is the approved winner
        final_score=95.0,
        submitted_at=None,
    )
    non_winner_submission = SubmissionModel(
        round_id=round_obj.id,
        user_id=photographer2.id,
        title="Mountain Landscape",
        status="submitted",  # Not approved as winner
        final_score=80.0,
        submitted_at=None,
    )
    db_session.add_all([winner_submission, non_winner_submission])
    db_session.commit()

    return {
        "organizer": organizer,
        "voter1": voter1,
        "voter2": voter2,
        "photographer1": photographer1,
        "photographer2": photographer2,
        "contest": contest,
        "round": round_obj,
        "winner_submission": winner_submission,
        "non_winner_submission": non_winner_submission,
    }


def test_user_can_vote_on_winner_submission(client, vote_test_data):
    """Test that a user can successfully vote on a winner (public) submission."""
    voter = vote_test_data["voter1"]
    submission = vote_test_data["winner_submission"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    response = client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["vote"]["submission_id"] == submission.id
    assert data["vote"]["user_id"] == voter.id


def test_user_cannot_vote_on_non_public_submission(client, vote_test_data):
    """Test that users cannot vote on non-winner submissions."""
    voter = vote_test_data["voter1"]
    submission = vote_test_data["non_winner_submission"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    response = client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "submission_not_public"


def test_user_cannot_vote_twice_on_same_submission(client, vote_test_data):
    """Test that a user can only vote once per submission."""
    voter = vote_test_data["voter1"]
    submission = vote_test_data["winner_submission"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    # First vote should succeed
    response1 = client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response1.status_code == 201

    # Second vote should fail
    response2 = client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 400
    data = response2.get_json()
    assert data["success"] is False
    assert data["error"] == "already_voted"


def test_user_can_unvote_submission(client, vote_test_data):
    """Test that a user can remove their vote."""
    voter = vote_test_data["voter1"]
    submission = vote_test_data["winner_submission"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    # Vote first
    client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Then unvote
    response = client.delete(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    # Verify can vote again after unvoting
    response2 = client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 201


def test_cannot_unvote_without_voting(client, vote_test_data):
    """Test that unvoting without a vote returns 404."""
    voter = vote_test_data["voter1"]
    submission = vote_test_data["winner_submission"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    response = client.delete(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "vote_not_found"


def test_get_submission_vote_count(client, vote_test_data):
    """Test getting vote count for a submission."""
    voter1 = vote_test_data["voter1"]
    voter2 = vote_test_data["voter2"]
    submission = vote_test_data["winner_submission"]
    token1 = create_jwt_token(voter1.id, username=voter1.username, role="participant")
    token2 = create_jwt_token(voter2.id, username=voter2.username, role="participant")

    # Two users vote
    client.post(f"/api/votes/{submission.id}", headers={"Authorization": f"Bearer {token1}"})
    client.post(f"/api/votes/{submission.id}", headers={"Authorization": f"Bearer {token2}"})

    # Get vote count (public endpoint, no auth required)
    response = client.get(f"/api/votes/{submission.id}/count")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["vote_count"] == 2


def test_get_vote_status(client, vote_test_data):
    """Test checking if user has voted on a submission."""
    voter = vote_test_data["voter1"]
    submission = vote_test_data["winner_submission"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    # Check status before voting
    response1 = client.get(
        f"/api/votes/{submission.id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response1.status_code == 200
    data1 = response1.get_json()
    assert data1["user_has_voted"] is False
    assert data1["total_votes"] == 0

    # Vote
    client.post(f"/api/votes/{submission.id}", headers={"Authorization": f"Bearer {token}"})

    # Check status after voting
    response2 = client.get(
        f"/api/votes/{submission.id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 200
    data2 = response2.get_json()
    assert data2["user_has_voted"] is True
    assert data2["total_votes"] == 1


def test_get_my_votes(client, vote_test_data):
    """Test getting user's vote history."""
    voter = vote_test_data["voter1"]
    submission1_id = vote_test_data["winner_submission"].id
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    # Create another winner for voting on
    db_session = FactoryDatabase.get_database("POSTGREE").session
    photographer3 = UserModel(
        username="photographer3",
        email="photo3@example.com",
        password_hash="hashed_pw",
        full_name="Photographer 3",
        status="active",
    )
    db_session.add(photographer3)
    db_session.commit()

    submission2 = SubmissionModel(
        round_id=vote_test_data["round"].id,
        user_id=photographer3.id,
        title="Another Winner Photo",
        status="winner",
        final_score=92.0,
        submitted_at=None,
    )
    db_session.add(submission2)
    db_session.commit()
    submission2_id = submission2.id

    # Vote on both
    client.post(f"/api/votes/{submission1_id}", headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/votes/{submission2_id}", headers={"Authorization": f"Bearer {token}"})

    # Get my votes
    response = client.get(
        "/api/votes/my-votes",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["count"] == 2
    vote_submission_ids = [v["submission_id"] for v in data["votes"]]
    assert submission1_id in vote_submission_ids
    assert submission2_id in vote_submission_ids


def test_vote_on_nonexistent_submission(client, vote_test_data):
    """Test voting on a submission that doesn't exist."""
    voter = vote_test_data["voter1"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    response = client.post(
        "/api/votes/99999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "submission_not_found"


def test_get_vote_count_for_nonexistent_submission(client):
    """Test getting vote count for nonexistent submission."""
    response = client.get("/api/votes/99999/count")

    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "submission_not_found"


def test_voting_prevents_duplicate_votes_in_database(client, vote_test_data):
    """Test that the unique constraint in database prevents duplicate votes."""
    voter = vote_test_data["voter1"]
    submission = vote_test_data["winner_submission"]
    token = create_jwt_token(voter.id, username=voter.username, role="participant")

    # First vote succeeds
    response1 = client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response1.status_code == 201

    # Second vote fails
    response2 = client.post(
        f"/api/votes/{submission.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response2.status_code == 400

    # Verify only one vote exists in database
    db_session = FactoryDatabase.get_database("POSTGREE").session
    vote_count = db_session.query(VoteModel).filter_by(
        user_id=voter.id,
        submission_id=submission.id
    ).count()
    assert vote_count == 1
