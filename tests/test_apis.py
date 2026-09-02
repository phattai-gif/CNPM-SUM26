#!/usr/bin/env python
import sys
import json
sys.path.insert(0, "src")

from create_app import create_app

app = create_app()
client = app.test_client()

# Test API endpoints
api_tests = [
    # Auth APIs
    ('POST', '/auth/check_router', {}, None),
    ('POST', '/auth/signup', {'username': 'test', 'email': 'test@test.com', 'password': 'test', 'passwordconfirm': 'test'}, None),
    ('POST', '/auth/login', {'username': 'test', 'password': 'test'}, None),
    
    # Contest APIs
    ('GET', '/contest/list', {}, None),
    ('GET', '/contest', {}, None),
    
    # Submission APIs
    ('GET', '/submission/list', {}, None),
    
    # Gallery API
    ('GET', '/gallery/api/submissions', {}, None),
    
    # AI Detection
    ('GET', '/ai-detection/health', {}, None),
    
    # Judge API
    ('GET', '/judge/submissions', {}, None),
]

print("Testing API endpoints:")
print("=" * 80)
for method, path, body, headers in api_tests:
    try:
        if method == 'GET':
            r = client.get(path)
        elif method == 'POST':
            r = client.post(path, json=body, content_type='application/json')
        
        status = r.status_code
        mimetype = r.mimetype
        size = len(r.get_data())
        
        # Try to parse JSON if applicable
        try:
            data = r.get_json()
            if isinstance(data, dict) and 'message' in data:
                msg = data.get('message', '')[:40]
                print(f"{method:6} {path:40} -> {status:3} | {msg}")
            else:
                print(f"{method:6} {path:40} -> {status:3} | JSON ({size} bytes)")
        except:
            print(f"{method:6} {path:40} -> {status:3} {mimetype:15} ({size} bytes)")
    except Exception as e:
        print(f"{method:6} {path:40} -> ERROR: {type(e).__name__}")

print("=" * 80)
print("\nAPI test completed!")
