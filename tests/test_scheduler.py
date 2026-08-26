import os
import sys
import io
import random
import string
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import jwt
from PIL import Image
from app import create_app
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.models.app import ContestModel, RoundModel, UserModel
from services.scheduler_service import SchedulerService


def generate_token(secret_key, user_id=1, username='testuser', role='participant'):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def create_sample_image(width=100, height=100, color=(255, 0, 0)):
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def create_db_user(session, role="organizer"):
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    user = UserModel(
        username=f"user_{rand_str}",
        email=f"user_{rand_str}@example.com",
        password_hash="pbkdf2:sha256:fakehash",
        full_name=f"Test User {rand_str}",
        status="active"
    )
    session.add(user)
    session.commit()
    return user.id


# -----------------------------------------------------------------------------
# 1. Contest Tests (Cases 1 - 4)
# -----------------------------------------------------------------------------

def test_contest_upcoming_before_start_date():
    """Case 1: Contest upcoming + chưa đến start_date -> không đổi."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Future Contest",
            slug=f"future-contest-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="upcoming",
            start_date=now + timedelta(days=2),
            end_date=now + timedelta(days=10)
        )
        session.add(contest)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(ContestModel).filter_by(id=contest.id).first()
        assert updated.status == "upcoming"


def test_contest_upcoming_start_date_reached():
    """Case 2: Contest upcoming + đã đến start_date -> chuyển ongoing."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Start Contest",
            slug=f"start-contest-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="upcoming",
            start_date=now - timedelta(minutes=5),
            end_date=now + timedelta(days=5)
        )
        session.add(contest)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(ContestModel).filter_by(id=contest.id).first()
        assert updated.status == "ongoing"


def test_contest_ongoing_before_end_date():
    """Case 3: Contest ongoing + chưa đến end_date -> không đổi."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Ongoing Contest",
            slug=f"ongoing-contest-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=5)
        )
        session.add(contest)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(ContestModel).filter_by(id=contest.id).first()
        assert updated.status == "ongoing"


def test_contest_ongoing_end_date_reached():
    """Case 4: Contest ongoing + đã đến end_date -> chuyển ended."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="End Contest",
            slug=f"end-contest-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing",
            start_date=now - timedelta(days=5),
            end_date=now - timedelta(minutes=1)
        )
        session.add(contest)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(ContestModel).filter_by(id=contest.id).first()
        assert updated.status == "ended"


# -----------------------------------------------------------------------------
# 2. Round Tests (Cases 5 - 8)
# -----------------------------------------------------------------------------

def test_round_upcoming_before_start_date():
    """Case 5: Round upcoming + chưa đến start_date -> không đổi."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Parent Contest 1",
            slug=f"parent-1-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Future Round",
            status="upcoming",
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=5)
        )
        session.add(rnd)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(RoundModel).filter_by(id=rnd.id).first()
        assert updated.status == "upcoming"


def test_round_upcoming_start_date_reached():
    """Case 6: Round upcoming + đã đến start_date -> chuyển ongoing."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Parent Contest 2",
            slug=f"parent-2-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Start Round",
            status="upcoming",
            start_date=now - timedelta(minutes=10),
            end_date=now + timedelta(days=5)
        )
        session.add(rnd)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(RoundModel).filter_by(id=rnd.id).first()
        assert updated.status == "ongoing"


def test_round_ongoing_before_end_date():
    """Case 7: Round ongoing + chưa đến end_date -> không đổi."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Parent Contest 3",
            slug=f"parent-3-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Active Round",
            status="ongoing",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=3)
        )
        session.add(rnd)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(RoundModel).filter_by(id=rnd.id).first()
        assert updated.status == "ongoing"


def test_round_ongoing_end_date_reached():
    """Case 8: Round ongoing + đã đến end_date -> chuyển grading."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Parent Contest 4",
            slug=f"parent-4-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Grading Round",
            status="ongoing",
            start_date=now - timedelta(days=5),
            end_date=now - timedelta(minutes=1)
        )
        session.add(rnd)
        session.commit()

        service = SchedulerService()
        service.check_and_update_statuses()

        updated = session.query(RoundModel).filter_by(id=rnd.id).first()
        assert updated.status == "grading"


# -----------------------------------------------------------------------------
# 3. Idempotency Test (Case 9)
# -----------------------------------------------------------------------------

def test_scheduler_idempotency():
    """Case 9: Chạy scheduler 2 lần liên tiếp -> không bị chuyển trạng thái sai/lặp."""
    app = create_app()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Idempotent Contest",
            slug=f"idempotent-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="upcoming",
            start_date=now - timedelta(minutes=5),
            end_date=now + timedelta(days=5)
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Idempotent Round",
            status="upcoming",
            start_date=now - timedelta(minutes=5),
            end_date=now + timedelta(days=5)
        )
        session.add(rnd)
        session.commit()

        service = SchedulerService()

        # Run 1
        service.check_and_update_statuses()
        c1 = session.query(ContestModel).filter_by(id=contest.id).first()
        r1 = session.query(RoundModel).filter_by(id=rnd.id).first()
        assert c1.status == "ongoing"
        assert r1.status == "ongoing"

        # Run 2
        service.check_and_update_statuses()
        c2 = session.query(ContestModel).filter_by(id=contest.id).first()
        r2 = session.query(RoundModel).filter_by(id=rnd.id).first()
        assert c2.status == "ongoing"
        assert r2.status == "ongoing"


# -----------------------------------------------------------------------------
# 4. Submission Validation Tests (Cases 10 - 13)
# -----------------------------------------------------------------------------

def test_participant_submit_round_upcoming():
    """Case 10: Participant submit khi Round upcoming -> bị từ chối (400)."""
    app = create_app()
    client = app.test_client()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")
        part_id = create_db_user(session, role="participant")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Submit Test Contest 1",
            slug=f"sub-contest-1-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Upcoming Round Submission",
            status="upcoming"
        )
        session.add(rnd)
        session.commit()

        token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=part_id)
        img_bytes = create_sample_image()

        data = {
            'round_id': str(rnd.id),
            'title': 'Test Submission Upcoming',
            'film_stock': 'Kodak Portra 400',
            'status': 'submitted',
            'file': (io.BytesIO(img_bytes), 'test.jpg', 'image/jpeg')
        }

        res = client.post('/submissions', data=data, content_type='multipart/form-data', headers={'Authorization': f'Bearer {token}'})
        assert res.status_code == 400


def test_participant_submit_round_ongoing():
    """Case 11: Participant submit khi Round ongoing -> cho phép."""
    app = create_app()
    client = app.test_client()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")
        part_id = create_db_user(session, role="participant")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Submit Test Contest 2",
            slug=f"sub-contest-2-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Ongoing Round Submission",
            status="ongoing"
        )
        session.add(rnd)
        session.commit()

        token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=part_id)
        img_bytes = create_sample_image()

        data = {
            'round_id': str(rnd.id),
            'title': 'Test Submission Ongoing',
            'film_stock': 'Kodak Portra 400',
            'status': 'submitted',
            'file': (io.BytesIO(img_bytes), 'test.jpg', 'image/jpeg')
        }

        res = client.post('/submissions', data=data, content_type='multipart/form-data', headers={'Authorization': f'Bearer {token}'})
        print("RESPONSE DATA:", res.get_json())
        assert res.status_code == 201


def test_participant_submit_round_grading():
    """Case 12: Participant submit khi Round grading -> bị từ chối (400)."""
    app = create_app()
    client = app.test_client()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")
        part_id = create_db_user(session, role="participant")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Submit Test Contest 3",
            slug=f"sub-contest-3-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Grading Round Submission",
            status="grading"
        )
        session.add(rnd)
        session.commit()

        token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=part_id)
        img_bytes = create_sample_image()

        data = {
            'round_id': str(rnd.id),
            'title': 'Test Submission Grading',
            'film_stock': 'Kodak Portra 400',
            'status': 'submitted',
            'file': (io.BytesIO(img_bytes), 'test.jpg', 'image/jpeg')
        }

        res = client.post('/submissions', data=data, content_type='multipart/form-data', headers={'Authorization': f'Bearer {token}'})
        assert res.status_code == 400


def test_participant_submit_round_ended():
    """Case 13: Participant submit khi Round ended -> bị từ chối (400)."""
    app = create_app()
    client = app.test_client()
    with app.app_context():
        session = db_factory.get_database('POSTGREE').session
        user_id = create_db_user(session, role="organizer")
        part_id = create_db_user(session, role="participant")

        now = datetime.now(timezone.utc)
        contest = ContestModel(
            title="Submit Test Contest 4",
            slug=f"sub-contest-4-{int(now.timestamp())}-{random.randint(1000, 9999)}",
            created_by=user_id,
            status="ongoing"
        )
        session.add(contest)
        session.commit()

        rnd = RoundModel(
            contest_id=contest.id,
            round_number=1,
            title="Ended Round Submission",
            status="ended"
        )
        session.add(rnd)
        session.commit()

        token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=part_id)
        img_bytes = create_sample_image()

        data = {
            'round_id': str(rnd.id),
            'title': 'Test Submission Ended',
            'film_stock': 'Kodak Portra 400',
            'status': 'submitted',
            'file': (io.BytesIO(img_bytes), 'test.jpg', 'image/jpeg')
        }

        res = client.post('/submissions', data=data, content_type='multipart/form-data', headers={'Authorization': f'Bearer {token}'})
        assert res.status_code == 400


# -----------------------------------------------------------------------------
# 5. Error Handling Test (Case 14)
# -----------------------------------------------------------------------------

def test_scheduler_error_handling():
    """Case 14: Scheduler gặp lỗi trên entity -> không crash, log lỗi, tiếp tục chạy."""
    app = create_app()
    with app.app_context():
        mock_repo = MagicMock()
        mock_repo.get_contests_by_status.side_effect = Exception("Database connection error")
        mock_repo.get_rounds_by_status.return_value = []

        service = SchedulerService(repository=mock_repo)
        service.check_and_update_statuses()
        assert mock_repo.get_contests_by_status.called
