import os
import sys
from datetime import datetime, timezone, timedelta

import jwt
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Ensure tests use an in-memory SQLite database
os.environ.setdefault('DATABASE_URI', 'sqlite:///:memory:')

from app import create_app
from infrastructure.databases.factory_database import FactoryDatabase
from infrastructure.models.app.app_user_model import UserModel
from infrastructure.models.app.app_contest_model import ContestModel
from infrastructure.models.app.app_round_model import RoundModel
from infrastructure.models.app.app_submission_model import SubmissionModel
from infrastructure.models.app.app_ai_flag_model import AIFlagModel


def make_token(app, user_id, role):
    return jwt.encode(
        {
            'user_id': user_id,
            'role': role,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
        },
        app.config['SECRET_KEY'],
        algorithm='HS256',
    )


def setup_minimal_data(session):
    # create an organizer and a participant
    suffix = uuid.uuid4().hex[:6]
    org = UserModel(username=f'org1_{suffix}', email=f'org1_{suffix}@example.com', password_hash='x')
    part = UserModel(username=f'part1_{suffix}', email=f'part1_{suffix}@example.com', password_hash='x')
    session.add_all([org, part])
    session.commit()

    # contest + round
    contest = ContestModel(title='TCT', slug=f'tct-{suffix}', created_by=org.id, status='running')
    session.add(contest)
    session.commit()

    round_ = RoundModel(contest_id=contest.id, round_number=1, title='R1', status='open')
    session.add(round_)
    session.commit()

    return org, part, contest, round_


def create_flagged_submission(session, participant, round_, contest, confidence=42.5, risk='medium'):
    # ensure unique title to avoid UNIQUE constraint collisions
    title = f"Flagged pic {uuid.uuid4().hex[:8]}"
    sub = SubmissionModel(round_id=round_.id, user_id=participant.id, title=title, status='flagged')
    session.add(sub)
    session.commit()

    flag = AIFlagModel(submission_id=sub.id, flag_type='AI_METADATA', confidence_score=confidence, risk_level=risk, status='flagged')
    session.add(flag)
    session.commit()
    return sub, flag


def test_flagged_submissions_api_includes_confidence_and_risk():
    app = create_app()
    client = app.test_client()

    db = FactoryDatabase.get_database('POSTGREE')
    session = db.session

    # ensure schema exists
    app_ctx = app.app_context()
    app_ctx.push()

    try:
        org, part, contest, round_ = setup_minimal_data(session)

        sub, flag = create_flagged_submission(session, part, round_, contest, confidence=77.25, risk='high')

        token = make_token(app, org.id, 'organizer')
        headers = {'Authorization': f'Bearer {token}'}

        # list flagged submissions
        resp = client.get(f'/moderator/submissions?contest_id={contest.id}&status=flagged', headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'submissions' in data
        items = data['submissions']
        assert any(item['id'] == sub.id for item in items)

        found = next((i for i in items if i['id'] == sub.id), None)
        assert found is not None
        assert found['ai'] is not None
        assert found['ai']['confidence_score'] == float(flag.confidence_score)
        assert found['ai']['risk_level'] == flag.risk_level

        # ai-report endpoint returns ai_report and ai_flag details
        resp2 = client.get(f'/moderator/submissions/{sub.id}/ai-report?contest_id={contest.id}', headers=headers)
        assert resp2.status_code == 200
        report = resp2.get_json()
        assert 'ai_flag' in report
        assert report['ai_flag']['confidence_score'] == float(flag.confidence_score)
        assert report['ai_flag']['risk_level'] == flag.risk_level

    finally:
        session.close()
        app_ctx.pop()


def test_moderation_actions_update_database():
    app = create_app()
    client = app.test_client()

    db = FactoryDatabase.get_database('POSTGREE')
    session = db.session

    app_ctx = app.app_context()
    app_ctx.push()

    try:
        org, part, contest, round_ = setup_minimal_data(session)

        # create three separate flagged submissions to test each action
        sub1, flag1 = create_flagged_submission(session, part, round_, contest, confidence=10.0, risk='safe')
        sub2, flag2 = create_flagged_submission(session, part, round_, contest, confidence=90.0, risk='high')
        sub3, flag3 = create_flagged_submission(session, part, round_, contest, confidence=50.0, risk='medium')

        token = make_token(app, org.id, 'organizer')
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        # Approve sub1 - assert DB reflects API result
        r = client.post(f'/moderator/submissions/{sub1.id}/approve', headers=headers, json={'contest_id': contest.id})
        assert r.status_code == 200
        j = r.get_json()
        assert 'result' in j
        api_sub_status = j['result'].get('submission_status')
        api_flag_status = j['result'].get('ai_flag_status')
        assert api_sub_status is not None
        assert api_flag_status is not None

        # Verify in DB matches API response
        session.expire_all()
        db_flag1 = session.query(AIFlagModel).filter_by(id=flag1.id).one()
        db_sub1 = session.query(SubmissionModel).filter_by(id=sub1.id).one()
        assert db_flag1.status == api_flag_status
        assert db_sub1.status == api_sub_status

        # Reject sub2
        r2 = client.post(f'/moderator/submissions/{sub2.id}/reject', headers=headers, json={'contest_id': contest.id})
        assert r2.status_code == 200
        j2 = r2.get_json()
        assert 'result' in j2
        api_sub_status2 = j2['result'].get('submission_status')
        api_flag_status2 = j2['result'].get('ai_flag_status')
        assert api_sub_status2 is not None
        assert api_flag_status2 is not None

        session.expire_all()
        db_flag2 = session.query(AIFlagModel).filter_by(id=flag2.id).one()
        db_sub2 = session.query(SubmissionModel).filter_by(id=sub2.id).one()
        assert db_flag2.status == api_flag_status2
        assert db_sub2.status == api_sub_status2

        # Dismiss sub3
        r3 = client.post(f'/moderator/submissions/{sub3.id}/dismiss-flag', headers=headers, json={'contest_id': contest.id})
        assert r3.status_code == 200
        j3 = r3.get_json()
        assert 'result' in j3
        api_sub_status3 = j3['result'].get('submission_status')
        api_flag_status3 = j3['result'].get('ai_flag_status')
        assert api_sub_status3 is not None
        assert api_flag_status3 is not None

        session.expire_all()
        db_flag3 = session.query(AIFlagModel).filter_by(id=flag3.id).one()
        db_sub3 = session.query(SubmissionModel).filter_by(id=sub3.id).one()
        assert db_flag3.status == api_flag_status3
        assert db_sub3.status == api_sub_status3

    finally:
        session.close()
        app_ctx.pop()
