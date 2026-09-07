import os
import sys
import jwt
from datetime import datetime, timedelta, timezone

os.environ['TESTING'] = 'True'
os.environ['POSTGREE_DATABASE_URL'] = 'sqlite:///:memory:'

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app
from infrastructure.databases.factory_database import FactoryDatabase as db_factory
from infrastructure.databases.base import Base
from infrastructure.models.app import (
    UserModel,
    ContestModel,
    RoundModel,
    CriteriaModel,
    SubmissionModel,
    JudgeAssignmentModel,
    ScoreModel,
    ScoreFeedbackModel,
)
from services.score_service import ScoreService


def generate_token(secret_key, user_id=1, username='judge1', role='judge'):
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


def setup_db(app):
    with app.app_context():
        db = db_factory.get_database('POSTGREE')
        try:
            Base.metadata.create_all(db.engine)
        except Exception:
            pass
        session = db.session

        # Clear existing data for clean run
        session.query(ScoreModel).delete()
        session.query(ScoreFeedbackModel).delete()
        session.query(JudgeAssignmentModel).delete()
        session.query(SubmissionModel).delete()
        session.query(CriteriaModel).delete()
        session.query(RoundModel).delete()
        session.query(ContestModel).delete()
        session.query(UserModel).delete()
        session.commit()

        # Seed test users
        judge1 = UserModel(id=10, username='judge1', email='j1@example.com', password_hash='hash', status='active')
        judge2 = UserModel(id=11, username='judge2', email='j2@example.com', password_hash='hash', status='active')
        participant = UserModel(id=12, username='part1', email='p1@example.com', password_hash='hash', status='active')
        organizer = UserModel(id=13, username='org1', email='o1@example.com', password_hash='hash', status='active')
        session.add_all([judge1, judge2, participant, organizer])
        session.commit()

        # Seed contest, round, criteria
        contest = ContestModel(id=1, title='Test Contest', slug='test-contest', created_by=13)
        session.add(contest)
        session.commit()

        round_obj = RoundModel(id=1, contest_id=1, round_number=1, title='Round 1', status='active')
        session.add(round_obj)
        session.commit()

        crit1 = CriteriaModel(id=1, round_id=1, name='Composition', max_score=40.0, weight=1.0)
        crit2 = CriteriaModel(id=2, round_id=1, name='Exposure', max_score=30.0, weight=1.0)
        session.add_all([crit1, crit2])

        # Seed submission
        sub1 = SubmissionModel(id=100, round_id=1, user_id=12, title='Submission #100', status='submitted')
        session.add(sub1)

        # Assign Judge 10 to Round 1 / Submission 100
        assignment = JudgeAssignmentModel(id=1, round_id=1, judge_id=10, submission_id=100)
        session.add(assignment)
        session.commit()


def test_judge_ui_unauthenticated():
    app = create_app()
    setup_db(app)
    client = app.test_client()

    res = client.get('/judge/100')
    assert res.status_code in (401, 302)


def test_judge_ui_forbidden_for_participant():
    app = create_app()
    setup_db(app)
    client = app.test_client()

    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=12, role='participant')
    res = client.get('/judge/100', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code in (403, 302)


def test_judge_ui_forbidden_for_organizer_unassigned():
    app = create_app()
    setup_db(app)
    client = app.test_client()

    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=13, role='organizer')
    res = client.get('/judge/100', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code in (403, 302)


def test_judge_ui_forbidden_for_unassigned_judge():
    app = create_app()
    setup_db(app)
    client = app.test_client()

    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=11, role='judge')
    res = client.get('/judge/100', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code in (403, 302)


def test_judge_ui_accessible_for_assigned_judge():
    app = create_app()
    setup_db(app)
    client = app.test_client()

    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='judge')
    res = client.get('/judge/100', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert 'Submission #100' in html
    assert 'Composition' in html


def test_judge_save_draft_persists_to_database():
    app = create_app()
    setup_db(app)
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='judge')

    # POST Save Draft
    res = client.post('/judge/100', data={
        '1': '35',
        '2': '25',
        'comment': 'Draft feedback note',
        'action': 'save_draft'
    }, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 302

    # Verify directly in Database
    session = db_factory.get_database('POSTGREE').session
    scores = session.query(ScoreModel).filter_by(submission_id=100, judge_id=10).all()
    assert len(scores) == 2
    score_map = {s.criteria_id: float(s.score_value) for s in scores}
    assert score_map[1] == 35.0
    assert score_map[2] == 25.0

    feedback = session.query(ScoreFeedbackModel).filter_by(submission_id=100, judge_id=10).first()
    assert feedback is not None
    assert feedback.summary_feedback == 'Draft feedback note'
    assert feedback.is_finalized is False

    # GET Judge UI again to confirm scores & feedback are loaded from DB
    res_get = client.get('/judge/100', headers={'Authorization': f'Bearer {token}'})
    assert res_get.status_code == 200
    html = res_get.get_data(as_text=True)
    assert '35' in html
    assert 'Draft feedback note' in html

    # Simulate re-login (new token) and verify score persists
    new_login_token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='judge')
    res_relogin = client.get('/judge/100', headers={'Authorization': f'Bearer {new_login_token}'})
    assert res_relogin.status_code == 200
    html_relogin = res_relogin.get_data(as_text=True)
    assert 'Draft feedback note' in html_relogin


def test_judge_finalize_locks_scores_and_prevents_edits():
    app = create_app()
    setup_db(app)
    client = app.test_client()
    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10, role='judge')

    # POST Finalize
    res_finalize = client.post('/judge/100', data={
        '1': '38',
        '2': '28',
        'comment': 'Finalized assessment',
        'action': 'finalize'
    }, headers={'Authorization': f'Bearer {token}'})
    assert res_finalize.status_code == 302

    # Verify DB finalized state
    session = db_factory.get_database('POSTGREE').session
    feedback = session.query(ScoreFeedbackModel).filter_by(submission_id=100, judge_id=10).first()
    assert feedback is not None
    assert feedback.is_finalized is True

    # 1. Attempt edit via UI POST -> should flash warning and prevent change
    res_edit_ui = client.post('/judge/100', data={
        '1': '10',
        '2': '10',
        'comment': 'Tampered comment',
        'action': 'save_draft'
    }, headers={'Authorization': f'Bearer {token}'})
    assert res_edit_ui.status_code == 302

    session.refresh(feedback)
    scores = session.query(ScoreModel).filter_by(submission_id=100, judge_id=10).all()
    score_map = {s.criteria_id: float(s.score_value) for s in scores}
    assert score_map[1] == 38.0
    assert feedback.summary_feedback == 'Finalized assessment'

    # 2. Attempt direct Service call edit -> rejected with feedback_finalized error
    score_svc = ScoreService()
    model, err = score_svc.submit_score(submission_id=100, judge_id=10, criteria_id=1, score_value=5.0)
    assert model is None
    assert err == 'feedback_finalized'

    fb_model, fb_err = score_svc.submit_feedback(submission_id=100, judge_id=10, summary_feedback='Direct edit', is_finalized=False)
    assert fb_model is None
    assert fb_err == 'feedback_finalized'

    # 3. Attempt direct Score API edit -> returns 409 Conflict
    api_score_res = client.post('/scores/submissions/100', json={'criteria_id': 1, 'score_value': 5.0}, headers={'Authorization': f'Bearer {token}'})
    assert api_score_res.status_code == 409

    api_fb_res = client.post('/scores/submissions/100/feedback', json={'summary_feedback': 'Direct API edit'}, headers={'Authorization': f'Bearer {token}'})
    assert api_fb_res.status_code == 409
