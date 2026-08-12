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


def create_token(user_id=1, username="organizer_test", role="organizer", secret_key="a_default_secret_key"):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def test_contest_full_flow():
    app = create_app()
    client = app.test_client()

    print("=" * 60)
    print("=== DANG CHAY TEST API TAO CUOC THI VA CAU HINH VONG THI ===")
    print("=" * 60)

    # Register an actual organizer user in DB to satisfy foreign key constraint created_by -> users.id
    org_user_data = generate_random_user(role="organizer")
    reg_res = client.post('/auth/signup', json=org_user_data)
    print(f"\n0. POST /auth/signup (Organizer) -> Status: {reg_res.status_code}")
    
    login_res = client.post('/auth/login', json={
        "username": org_user_data["username"],
        "password": org_user_data["password"]
    })
    login_data = login_res.get_json() or {}
    print(f"   POST /auth/login -> Status: {login_res.status_code}")
    
    organizer_token = login_data.get("token")
    if not organizer_token:
        # Fallback if DB not reachable
        secret_key = app.config.get('SECRET_KEY') or 'a_default_secret_key'
        organizer_token = create_token(user_id=1, role="organizer", secret_key=secret_key)
    
    participant_token = create_token(user_id=99999, role="participant", secret_key=app.config.get('SECRET_KEY') or 'a_default_secret_key')

    headers_org = {"Authorization": f"Bearer {organizer_token}"}
    headers_part = {"Authorization": f"Bearer {participant_token}"}

    # 1. Test Authorization Check (Participant cannot create contest)
    res = client.post('/organizer/contests', json={'title': 'Forbidden Contest'}, headers=headers_part)
    print(f"\n1. POST /organizer/contests (Participant) -> Status: {res.status_code}")
    assert res.status_code == 403

    # 2. Test Create Contest (Organizer)
    contest_payload = {
        'title': 'Cuoc thi Lap trinh CNTT 2026',
        'description': 'Cuoc thi lap trinh toan quoc cho sinh vien.',
        'rules': 'The le cuoc thi: Thi sinh lam bai ca nhan, khong gian lan.',
        'banner_url': 'https://example.com/banner.png',
        'status': 'draft',
        'start_date': '2026-09-01T08:00:00',
        'end_date': '2026-10-31T18:00:00'
    }
    res = client.post('/organizer/contests', json=contest_payload, headers=headers_org)
    print(f"\n2. POST /organizer/contests -> Status: {res.status_code}")
    res_data = res.get_json() or {}
    print(f"   Response: {res_data}")
    assert res.status_code == 201
    contest = res_data.get('contest', {})
    contest_id = contest.get('id')
    assert contest_id is not None
    assert contest['title'] == contest_payload['title']

    # 3. Test Get Contest Details
    res = client.get(f'/organizer/contests/{contest_id}', headers=headers_org)
    print(f"\n3. GET /organizer/contests/{contest_id} -> Status: {res.status_code}")
    assert res.status_code == 200
    res_data = res.get_json() or {}
    assert res_data['contest']['rules'] == contest_payload['rules']

    # 4. Test Update Rules (Thể lệ)
    rules_payload = {
        'rules': 'The le cap nhat: Bo sung quy dinh ve AI va Dao van.'
    }
    res = client.put(f'/organizer/contests/{contest_id}/rules', json=rules_payload, headers=headers_org)
    print(f"\n4. PUT /organizer/contests/{contest_id}/rules -> Status: {res.status_code}")
    assert res.status_code == 200
    assert res.get_json()['contest']['rules'] == rules_payload['rules']

    # 5. Test Create Round
    round_payload = {
        'round_number': 1,
        'title': 'Vong So loai',
        'description': 'Danh gia y tuong va mo hinh giai phap',
        'start_date': '2026-09-01T08:00:00',
        'end_date': '2026-09-15T18:00:00',
        'weight': 0.3,
        'status': 'upcoming'
    }
    res = client.post(f'/organizer/contests/{contest_id}/rounds', json=round_payload, headers=headers_org)
    print(f"\n5. POST /organizer/contests/{contest_id}/rounds -> Status: {res.status_code}")
    print(f"   Response: {res.get_json()}")
    assert res.status_code == 201
    round_obj = res.get_json().get('round', {})
    round_id = round_obj.get('id')
    assert round_id is not None

    # 6. Test Update Round
    update_round_payload = {'title': 'Vong So tuyen Cap nhat', 'status': 'ongoing'}
    res = client.put(f'/organizer/contests/{contest_id}/rounds/{round_id}', json=update_round_payload, headers=headers_org)
    print(f"\n6. PUT /organizer/contests/{contest_id}/rounds/{round_id} -> Status: {res.status_code}")
    assert res.status_code == 200
    assert res.get_json()['round']['title'] == update_round_payload['title']

    # 7. Test Create Criteria (Tiêu chí chấm điểm)
    criteria_payload = {
        'name': 'Tinh Sang Tao',
        'description': 'Danh gia muc do doc dao cua y tuong',
        'max_score': 10.0,
        'weight': 0.4
    }
    res = client.post(f'/organizer/contests/{contest_id}/rounds/{round_id}/criteria', json=criteria_payload, headers=headers_org)
    print(f"\n7. POST /organizer/contests/{contest_id}/rounds/{round_id}/criteria -> Status: {res.status_code}")
    assert res.status_code == 201
    criteria_obj = res.get_json().get('criteria', {})
    criteria_id = criteria_obj.get('id')
    assert criteria_id is not None

    # 8. Test Update Criteria
    update_criteria_payload = {'name': 'Tinh Sang Tao & Dot Pha', 'max_score': 20.0}
    res = client.put(f'/organizer/contests/{contest_id}/rounds/{round_id}/criteria/{criteria_id}', json=update_criteria_payload, headers=headers_org)
    print(f"\n8. PUT /organizer/contests/{contest_id}/rounds/{round_id}/criteria/{criteria_id} -> Status: {res.status_code}")
    assert res.status_code == 200
    assert res.get_json()['criteria']['name'] == update_criteria_payload['name']

    # 9. Test Bulk Contest Configuration API (Cập nhật thể lệ + vòng + tiêu chí đồng thời)
    config_payload = {
        'rules': 'The le hoan chinh cho tat ca cac vong.',
        'rounds': [
            {
                'round_number': 1,
                'title': 'Vong 1: Y Tuong',
                'description': 'Mo ta vong 1',
                'weight': 0.4,
                'criteria': [
                    {'name': 'Y tuong', 'max_score': 10.0, 'weight': 0.5},
                    {'name': 'Trinh bay', 'max_score': 10.0, 'weight': 0.5}
                ]
            },
            {
                'round_number': 2,
                'title': 'Vong Chung ket',
                'description': 'Thuyet trinh san pham',
                'weight': 0.6,
                'criteria': [
                    {'name': 'Do hoan thien san pham', 'max_score': 10.0, 'weight': 0.7},
                    {'name': 'Q&A voi Ban giam khao', 'max_score': 10.0, 'weight': 0.3}
                ]
            }
        ]
    }
    res = client.put(f'/organizer/contests/{contest_id}/configuration', json=config_payload, headers=headers_org)
    print(f"\n9. PUT /organizer/contests/{contest_id}/configuration -> Status: {res.status_code}")
    assert res.status_code == 200
    full_contest = res.get_json()['contest']
    assert full_contest['rules'] == config_payload['rules']
    assert len(full_contest['rounds']) == 2
    assert len(full_contest['rounds'][0]['criteria']) == 2
    assert len(full_contest['rounds'][1]['criteria']) == 2

    # 10. Test Delete Contest
    res = client.delete(f'/organizer/contests/{contest_id}', headers=headers_org)
    print(f"\n10. DELETE /organizer/contests/{contest_id} -> Status: {res.status_code}")
    assert res.status_code == 200

    print("\n" + "=" * 60)
    print("=== TOAN BO TEST API CONTEST DA THANH CONG! ===")
    print("=" * 60)


if __name__ == '__main__':
    test_contest_full_flow()
