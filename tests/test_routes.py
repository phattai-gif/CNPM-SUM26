#!/usr/bin/env python
import sys
sys.path.insert(0, "src")

from create_app import create_app

app = create_app()
client = app.test_client()

routes_to_test = [
    ('GET', '/'),
    ('GET', '/auth/login'),
    ('GET', '/auth/register'),
    ('GET', '/contests'),
    ('GET', '/submission'),
    ('GET', '/profile'),
    ('GET', '/my-submissions'),
    ('GET', '/gallery'),
    ('GET', '/judge'),
    ('GET', '/docs'),
    ('GET', '/auth/check_router'),
]

print("Testing routes:")
print("=" * 70)
for method, path in routes_to_test:
    try:
        if method == 'GET':
            r = client.get(path)
        status = r.status_code
        mimetype = r.mimetype
        size = len(r.get_data())
        print(f"{method:6} {path:30} -> {status:3} {mimetype:20} ({size} bytes)")
    except Exception as e:
        print(f"{method:6} {path:30} -> ERROR: {type(e).__name__}: {str(e)[:40]}")

print("=" * 70)
print("\nAll route tests completed!")
