#!/usr/bin/env python
import sys
import json
sys.path.insert(0, "src")

from create_app import create_app

app = create_app()
client = app.test_client()

# Test problematic endpoints
print("Detailed error check:")
print("=" * 80)

# Test /auth/check_router with POST (should be GET)
print("\n1. Testing /auth/check_router:")
r = client.get('/auth/check_router')
print(f"   GET /auth/check_router -> {r.status_code}")
print(f"   Response: {r.get_json()}")

r = client.post('/auth/check_router')
print(f"   POST /auth/check_router -> {r.status_code}")
if r.status_code == 500:
    print(f"   Response: {r.get_data(as_text=True)[:200]}")

# Test signup with proper data
print("\n2. Testing /auth/signup with valid data:")
r = client.post('/auth/signup', json={
    'username': 'testuser123',
    'email': 'test@example.com',
    'password': 'Test@1234',
    'passwordconfirm': 'Test@1234',
    'full_name': 'Test User'
})
print(f"   POST /auth/signup -> {r.status_code}")
data = r.get_json()
if data:
    print(f"   Message: {data.get('message', 'N/A')}")
    if 'errors' in data:
        print(f"   Errors: {data['errors']}")

# Test login
print("\n3. Testing /auth/login:")
r = client.post('/auth/login', json={
    'username': 'testuser123',
    'password': 'Test@1234'
})
print(f"   POST /auth/login -> {r.status_code}")
data = r.get_json()
if data:
    print(f"   Message: {data.get('message', 'N/A')}")

print("\n" + "=" * 80)
print("Detailed error check completed!")
