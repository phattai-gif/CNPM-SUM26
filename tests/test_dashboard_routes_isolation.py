import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
if not os.environ.get('DATABASE_URI'):
    os.environ['DATABASE_URI'] = 'sqlite:///:memory:'

from infrastructure.databases.factory_database import FactoryDatabase

# Mock DB session for test
mock_user = MagicMock()
mock_user.status = 'active'
dummy_db = MagicMock()
dummy_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user
FactoryDatabase.get_database = MagicMock(return_value=dummy_db)

from flask import Flask
import jwt
from datetime import datetime, timedelta, timezone
from api.routes import register_routes


@pytest.fixture
def app():
    app = Flask(__name__, template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend/templates')))
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-change-me-in-production-32chars'
    register_routes(app)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _make_token(app, role, user_id=1, username="testuser"):
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def test_organizer_dashboard_access_for_organizer(app, client):
    token = _make_token(app, 'organizer', user_id=10, username="org_user")
    headers = {'Authorization': f'Bearer {token}'}
    
    response = client.get('/organizer/dashboard', headers=headers)
    assert response.status_code == 200
    assert b'Organizer Dashboard' in response.data


def test_admin_dashboard_access_for_admin(app, client):
    token = _make_token(app, 'admin', user_id=1, username="admin_user")
    headers = {'Authorization': f'Bearer {token}'}
    
    response = client.get('/admin/dashboard', headers=headers)
    assert response.status_code == 200
    assert b'Admin Dashboard' in response.data


def test_admin_cannot_access_organizer_dashboard_html(app, client):
    token = _make_token(app, 'admin', user_id=1, username="admin_user")
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'text/html'
    }
    
    response = client.get('/organizer/dashboard', headers=headers)
    assert response.status_code == 302
    assert '/admin/dashboard' in response.headers['Location']


def test_organizer_cannot_access_admin_dashboard_html(app, client):
    token = _make_token(app, 'organizer', user_id=10, username="org_user")
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'text/html'
    }
    
    response = client.get('/admin/dashboard', headers=headers)
    assert response.status_code == 302
    assert '/organizer/dashboard' in response.headers['Location']


def test_unauthenticated_dashboard_redirects_to_login(client):
    headers = {'Accept': 'text/html'}
    
    resp1 = client.get('/organizer/dashboard', headers=headers)
    assert resp1.status_code == 302
    assert '/auth/login' in resp1.headers['Location']

    resp2 = client.get('/admin/dashboard', headers=headers)
    assert resp2.status_code == 302
    assert '/auth/login' in resp2.headers['Location']
