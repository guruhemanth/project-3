"""Email sending: SendGrid API in production, local SMTP (MailHog) in dev.

Selection: if SENDGRID_API_KEY is set (and looks valid) we use SendGrid, otherwise
we fall back to SMTP -> localhost:1025 (MailHog) so the flow works without external creds.
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from ..config import settings


def send_email(to: str, subject: str, body: str) -> bool:
    if settings.sendgrid_api_key and settings.sendgrid_api_key.startswith("SG"):
        return _send_sendgrid(to, subject, body)
    return _send_smtp(to, subject, body)


def _send_smtp(to: str, subject: str, body: str) -> bool:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.from_email
    msg["To"] = to
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.sendmail(settings.from_email, [to], msg.as_string())
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[email] SMTP send failed: {exc}")
        return False


def _send_sendgrid(to: str, subject: str, body: str) -> bool:
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(settings.sendgrid_api_key)
        mail = Mail(
            from_email=settings.from_email,
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )
        resp = sg.send(mail)
        return 200 <= resp.status_code < 300
    except Exception as exc:  # pragma: no cover
        print(f"[email] SendGrid send failed: {exc}")
        return False
