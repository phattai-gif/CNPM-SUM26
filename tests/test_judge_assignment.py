import sys
import os
import random
import string
import jwt

# UTF-8 stdout configuration for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app


def generate_random_user(role="organizer"):
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return {
        "username": f"user_{rand_str}",
        "email": f"user_{rand_str}@example.com",
        "password": "password123",
        "passwordconfirm": "password123",
        "full_name": f"Test User {rand_str}",
        "role": role
    }


def create_token(user_id=1, username="test_user", role="organizer", secret_key="a_default_secret_key"):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def test_judge_assignment_flow():
    app = create_app()
    client = app.test_client()

    print("=" * 60)
    print("=== DANG CHAY TEST API PHAN CONG GIAM KHAO (ASSIGN JUDGE API) ===")
    print("=" * 60)

    # 1. Register Organizer, Judge, and Participant users
    org_user_data = generate_random_user(role="organizer")
    client.post('/auth/signup', json=org_user_data)
    login_res = client.post('/auth/login', json={
        "username": org_user_data["username"],
        "password": org_user_data["password"]
    })
    org_login_data = login_res.get_json() or {}
    org_token = org_login_data.get("token") or create_token(user_id=1, role="organizer", secret_key=app.config.get('SECRET_KEY') or 'a_default_secret_key')
    headers_org = {"Authorization": f"Bearer {org_token}"}

    judge_user_data = generate_random_user(role="judge")
    client.post('/auth/signup', json=judge_user_data)
    login_res = client.post('/auth/login', json={
        "username": judge_user_data["username"],
        "password": judge_user_data["password"]
    })
    judge_login_data = login_res.get_json() or {}
    judge_user_id = judge_login_data.get("user", {}).get("id") or 2
    judge_token = judge_login_data.get("token") or create_token(user_id=judge_user_id, role="judge", secret_key=app.config.get('SECRET_KEY') or 'a_default_secret_key')
    headers_judge = {"Authorization": f"Bearer {judge_token}"}

    participant_token = create_token(user_id=9999, role="participant", secret_key=app.config.get('SECRET_KEY') or 'a_default_secret_key')
    headers_part = {"Authorization": f"Bearer {participant_token}"}

    # 2. Get Available Judges list
    res = client.get('/organizer/judges', headers=headers_org)
    print(f"\n1. GET /organizer/judges -> Status: {res.status_code}")
    assert res.status_code == 200
    judges_list = res.get_json().get('judges', [])
    print(f"   Found {len(judges_list)} candidate judges.")

    # 3. Create Contest and Round
    contest_res = client.post('/organizer/contests', json={
        'title': 'Cuoc thi Anh Phim 2026',
        'description': 'Cuoc thi danh cho nhiep anh gia nhan tao',
        'status': 'draft'
    }, headers=headers_org)
    assert contest_res.status_code == 201
    contest_id = contest_res.get_json()['contest']['id']

    round_res = client.post(f'/organizer/contests/{contest_id}/rounds', json={
        'title': 'Vong So Tuyen',
        'round_number': 1,
        'weight': 1.0
    }, headers=headers_org)
    assert round_res.status_code == 201
    round_id = round_res.get_json()['round']['id']
    print(f"\n2. Created Contest #{contest_id} & Round #{round_id}")

    # 4. Access control check (Participant cannot assign judge)
    res = client.post(f'/organizer/contests/{contest_id}/rounds/{round_id}/judges', json={
        'judge_id': judge_user_id
    }, headers=headers_part)
    print(f"\n3. POST assign judge (Participant token) -> Status: {res.status_code}")
    assert res.status_code == 403

    # 5. Assign Judge to Round (Organizer)
    res = client.post(f'/organizer/contests/{contest_id}/rounds/{round_id}/judges', json={
        'judge_id': judge_user_id
    }, headers=headers_org)
    print(f"\n4. POST /organizer/contests/{contest_id}/rounds/{round_id}/judges -> Status: {res.status_code}")
    res_data = res.get_json() or {}
    print(f"   Response: {res_data}")
    assert res.status_code == 201
    assignment = res_data.get('assignment', {})
    assert assignment.get('judge_id') == judge_user_id
    assert assignment.get('round_id') == round_id

    # 6. Get Assigned Judges for Round
    res = client.get(f'/organizer/contests/{contest_id}/rounds/{round_id}/judges', headers=headers_org)
    print(f"\n5. GET /organizer/contests/{contest_id}/rounds/{round_id}/judges -> Status: {res.status_code}")
    assert res.status_code == 200
    assigned_list = res.get_json().get('assignments', [])
    assert len(assigned_list) >= 1
    assert any(a['judge_id'] == judge_user_id for a in assigned_list)

    # 7. Judge views their own assignments
    res = client.get('/judge/assignments', headers=headers_judge)
    print(f"\n6. GET /judge/assignments (Judge token) -> Status: {res.status_code}")
    assert res.status_code == 200
    judge_assignments = res.get_json().get('assignments', [])
    assert any(a['round_id'] == round_id for a in judge_assignments)

    # 8. Unassign Judge from Round
    res = client.delete(f'/organizer/contests/{contest_id}/rounds/{round_id}/judges/{judge_user_id}', headers=headers_org)
    print(f"\n7. DELETE /organizer/contests/{contest_id}/rounds/{round_id}/judges/{judge_user_id} -> Status: {res.status_code}")
    assert res.status_code == 200

    # 9. Verify Judge list for round is now empty/updated
    res = client.get(f'/organizer/contests/{contest_id}/rounds/{round_id}/judges', headers=headers_org)
    assert res.status_code == 200
    assert len(res.get_json().get('assignments', [])) == 0

    print("\n" + "=" * 60)
    print("=== TOAN BO TEST API PHAN CONG GIAM KHAO DA THANH CONG! ===")
    print("=" * 60)


if __name__ == '__main__':
    test_judge_assignment_flow()
