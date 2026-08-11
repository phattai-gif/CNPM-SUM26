import sys
import os
import random
import string

# Thêm đường dẫn src vào sys.path để import app và các module dễ dàng
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app

def generate_random_user():
    rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return {
        "username": f"user_{rand_str}",
        "email": f"user_{rand_str}@example.com",
        "password": "password123",
        "passwordconfirm": "password123",
        "full_name": f"Test User {rand_str}",
        "role": "participant"
    }

def test_auth_flow():
    app = create_app()
    client = app.test_client()

    print("=" * 55)
    print("=== DANG CHAY TEST API AUTH TREN TERMINAL ===")
    print("=" * 55)

    # 1. Test Check Router
    res = client.get('/auth/check_router')
    print(f"\n1. GET /auth/check_router -> Status: {res.status_code}")
    print(f"   Response: {res.get_json()}")
    assert res.status_code == 200

    # 2. Test Signup
    user_data = generate_random_user()
    res = client.post('/auth/signup', json=user_data)
    print(f"\n2. POST /auth/signup -> Status: {res.status_code}")
    print(f"   Username tao moi: {user_data['username']}")
    print(f"   Response: {res.get_json()}")
    assert res.status_code == 201

    # 3. Test Login
    login_data = {
        "username": user_data["username"],
        "password": user_data["password"]
    }
    res = client.post('/auth/login', json=login_data)
    print(f"\n3. POST /auth/login -> Status: {res.status_code}")
    res_json = res.get_json() or {}
    print(f"   Response: {res_json}")
    assert res.status_code == 200

    token = res_json.get("token")
    assert token is not None

    # 4. Test GET /auth/me (với JWT Token)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get('/auth/me', headers=headers)
    print(f"\n4. GET /auth/me (VOI TOKEN) -> Status: {res.status_code}")
    print(f"   Response: {res.get_json()}")
    assert res.status_code == 200

    print("\n" + "=" * 55)
    print("=== TEST HOAN TAT SUCCESSFUL! ===")
    print("=" * 55)

if __name__ == '__main__':
    test_auth_flow()
