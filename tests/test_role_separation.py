import os
from dotenv import load_dotenv

load_dotenv()

import unittest
from unittest.mock import patch, MagicMock
import jwt
from flask import Flask
from api.routes import register_routes


class TestRoleSeparation(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test_secret'
        self.app.config['TESTING'] = True
        register_routes(self.app)
        self.client = self.app.test_client()

    def _make_token(self, user_id=1, username='testuser', role='participant'):
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role
        }
        return jwt.encode(payload, 'test_secret', algorithm='HS256')

    def test_admin_routes_forbidden_for_organizer(self):
        token = self._make_token(user_id=10, username='org1', role='organizer')
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.get('/admin/users', headers=headers)
        self.assertEqual(res.status_code, 403)

        res = self.client.get('/admin/contests', headers=headers)
        self.assertEqual(res.status_code, 403)

        res = self.client.get('/admin/audit-logs', headers=headers)
        self.assertEqual(res.status_code, 403)

    @patch('api.controllers.admin_controller.admin_user_service')
    @patch('infrastructure.databases.factory_database.FactoryDatabase.get_database')
    def test_admin_routes_accessible_for_admin(self, mock_db, mock_admin_service):
        mock_admin_service.list_users.return_value = ([], 0)

        mock_user = MagicMock()
        mock_user.status = 'active'

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_user
        mock_session.query.return_value.order_by.return_value.all.return_value = []
        mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
        mock_db.return_value.session = mock_session

        token = self._make_token(user_id=1, username='admin1', role='admin')
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.get('/admin/users', headers=headers)
        self.assertEqual(res.status_code, 200)

        res = self.client.get('/admin/contests', headers=headers)
        self.assertEqual(res.status_code, 200)

        res = self.client.get('/admin/audit-logs', headers=headers)
        self.assertEqual(res.status_code, 200)

    def test_organizer_routes_forbidden_for_admin(self):
        token = self._make_token(user_id=1, username='admin1', role='admin')
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.post('/organizer/contests', headers=headers, json={'title': 'Test'})
        self.assertEqual(res.status_code, 403)

        res = self.client.get('/organizer/judges', headers=headers)
        self.assertEqual(res.status_code, 403)

    @patch('api.controllers.judge_controller.judge_service')
    def test_organizer_routes_accessible_for_organizer(self, mock_judge_service):
        mock_judge_service.get_available_judges.return_value = []

        token = self._make_token(user_id=2, username='org1', role='organizer')
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.get('/organizer/judges', headers=headers)
        self.assertEqual(res.status_code, 200)

    def test_judge_routes_forbidden_for_participant(self):
        token = self._make_token(user_id=3, username='part1', role='participant')
        headers = {'Authorization': f'Bearer {token}'}

        res = self.client.get('/judge/assignments', headers=headers)
        self.assertEqual(res.status_code, 403)

        res = self.client.post('/scores/submissions/1', headers=headers, json={'criteria_id': 1, 'score_value': 10})
        self.assertEqual(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()
