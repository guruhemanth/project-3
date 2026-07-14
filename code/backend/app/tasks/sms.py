"""SMS sending: Twilio in production, logged otherwise.

When Twilio credentials are absent we log the message (dev). The request-OTP flow
calls this; the daily alert job only calls it when SMS is enabled AND the user's
phone is verified.
"""
from __future__ import annotations

from ..config import settings


def send_sms(to: str, body: str) -> bool:
    if not to:
        return False
    if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number:
        return _send_twilio(to, body)
    # Dev fallback: log instead of failing.
    print(f"[sms][dev] -> {to}: {body}")
    return True


def _send_twilio(to: str, body: str) -> bool:
    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(to=to, from_=settings.twilio_from_number, body=body)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[sms] Twilio send failed: {exc}")
        return False
