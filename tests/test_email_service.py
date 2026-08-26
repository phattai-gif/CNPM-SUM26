import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import create_app
from services.email_service import email_service


def test_email_service_sends_a_link_without_network(monkeypatch):
    app = create_app()
    app.config.update(
        SMTP_HOST='smtp.example.com',
        SMTP_PORT=587,
        SMTP_USERNAME='sender@example.com',
        SMTP_PASSWORD='app-password',
        SMTP_FROM='sender@example.com',
        SMTP_USE_TLS=True,
    )
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent['connection'] = (host, port, timeout)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent['tls'] = True

        def login(self, username, password):
            sent['login'] = (username, password)

        def send_message(self, message):
            sent['message'] = message

    monkeypatch.setattr('services.email_service.smtplib.SMTP', FakeSMTP)

    with app.app_context():
        assert email_service.send_token_email(
            'user@example.com',
            'Reset your password',
            'https://example.com/auth/reset-password?token=abc',
            'reset your password',
            '15 minutes',
        ) is True

    assert sent['connection'] == ('smtp.example.com', 587, 10)
    assert sent['tls'] is True
    assert sent['message']['To'] == 'user@example.com'
    assert 'token=abc' in sent['message'].get_content()
