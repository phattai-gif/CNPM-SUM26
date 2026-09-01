import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from src.create_app import create_app
from unittest.mock import MagicMock
from src.services.submission_service import SubmissionService

app = create_app()
app.config['TESTING'] = True

with app.test_client() as client:
    # mimic the test setup
    # Minimal generate_token and MockObject as in tests
    import jwt
    from datetime import datetime, timedelta, timezone

    def generate_token(secret_key, user_id=1, username='testuser', role='organizer'):
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

    class MockObject:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    token = generate_token(app.config.get('SECRET_KEY', 'a_default_secret_key'), user_id=10)

    mock_sub = MockObject(id=101, user_id=10, status="submitted", title="Official Entry")
    mock_file = MockObject(id=1, image_hd_url="https://example.com/hd.jpg")
    mock_meta = MockObject(film_stock="Kodak Portra 400")

    mock_repo = MagicMock()
    mock_repo.get_by_id_with_details.return_value = (mock_sub, mock_file, mock_meta)

    custom_svc = SubmissionService(submission_repo=mock_repo)

    # inject into controller
    import src.api.controllers.submission_controller as sc
    sc.submission_service = custom_svc
    # also patch alternate import path used by app
    import sys
    if 'api.controllers.submission_controller' in sys.modules:
        sys.modules['api.controllers.submission_controller'].submission_service = custom_svc

    # Direct call to service for debugging
    try:
        svc_res = custom_svc.submit_draft(101, 10)
        print('direct service result:', svc_res)
    except Exception as e:
        print('direct service raised:', type(e), e)

    res = client.post('/submissions/101/submit', headers={'Authorization': f'Bearer {token}'})
    print('STATUS:', res.status_code)
    try:
        print('DATA:', res.get_json())
    except Exception as e:
        print('Failed to decode JSON:', e)
        print(res.data)
