import smtplib
from email.message import EmailMessage
from typing import Optional

from flask import current_app


class EmailService:
    """Send transactional authentication emails through configured SMTP."""

    def is_configured(self) -> bool:
        return bool(current_app.config.get('SMTP_HOST'))

    def send_token_email(
        self,
        recipient: str,
        subject: str,
        action_url: str,
        action_label: str,
        expires_in: str,
    ) -> bool:
        smtp_host = current_app.config.get('SMTP_HOST')
        if not smtp_host:
            return False

        try:
            message = EmailMessage()
            message['Subject'] = subject
            message['From'] = current_app.config.get('SMTP_FROM') or current_app.config.get('SMTP_USERNAME')
            message['To'] = recipient
            message.set_content(
                f"Use the link below to {action_label.lower()}.\n\n"
                f"{action_url}\n\n"
                f"This link expires in {expires_in}. If you did not request this, ignore this email."
            )
            smtp_port = int(current_app.config.get('SMTP_PORT', 587))
            smtp_timeout = int(current_app.config.get('SMTP_TIMEOUT', 10))
            use_ssl = current_app.config.get('SMTP_USE_SSL', False)
            smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
            with smtp_class(smtp_host, smtp_port, timeout=smtp_timeout) as server:
                if not use_ssl and current_app.config.get('SMTP_USE_TLS', True):
                    server.starttls()
                username = current_app.config.get('SMTP_USERNAME')
                password = current_app.config.get('SMTP_PASSWORD')
                if username and password:
                    server.login(username, password)
                server.send_message(message)
            return True
        except (OSError, smtplib.SMTPException) as exc:
            current_app.logger.exception('Failed to send authentication email: %s', exc)
            return False


email_service = EmailService()
