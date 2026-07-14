"""Celery tasks: scheduled daily alert sweep + on-demand test alert.

Alert windows are exactly the days [7, 3, 1] before a trial_end_date or
next_renewal_date. Each (subscription, channel, alert_type, date) is sent at most
once, enforced by the unique constraint on alert_logs (uq_alert_dedup).
"""
from __future__ import annotations

import datetime as dt
import time

from sqlalchemy.orm import joinedload

from .celery_app import celery_app
from ..database import SessionLocal
from ..models import (
    AlertLog,
    AlertPreference,
    AlertStatus,
    AlertType,
    Channel,
    SubStatus,
    Subscription,
    User,
)
from ..rate_limit import alert_limiter
from .email import send_email
from .sms import send_sms

WINDOWS = [7, 3, 1]


def _throttle():
    allowed, _, _, _ = alert_limiter.check("alert-job")
    if not allowed:
        time.sleep(1.0)


def _log(db, user, sub, channel: Channel, atype: AlertType, target: dt.date, status: AlertStatus, detail):
    db.add(AlertLog(
        user_id=user.id, subscription_id=sub.id, channel=channel, alert_type=atype,
        alert_date=target, status=status, detail=detail,
        sent_at=dt.datetime.now(dt.timezone.utc),
    ))
    db.commit()


def _already_sent(db, sub_id, channel: Channel, atype: AlertType, target: dt.date) -> bool:
    return db.query(AlertLog).filter_by(
        subscription_id=sub_id, channel=channel, alert_type=atype, alert_date=target
    ).first() is not None


def _send_channel(db, user: User, sub: Subscription, channel: Channel, atype: AlertType, target: dt.date) -> str:
    """Send one alert. Returns: 'noop' (already sent), 'sent', 'failed', 'skipped'."""
    if _already_sent(db, sub.id, channel, atype, target):
        return "noop"
    label = "trial ending" if atype == AlertType.trial_end else "renewal"
    subject = f"[SubTrack] Upcoming {label}: {sub.merchant_name}"
    body = (
        f"Hi {user.email},\n\n"
        f"Reminder: {sub.merchant_name} ({sub.amount} {sub.currency}, {sub.billing_cycle}) "
        f"{label} on {target.isoformat()}.\n\n— SubTrack"
    )
    _throttle()
    if channel == Channel.email:
        ok = send_email(user.email, subject, body)
        _log(db, user, sub, channel, atype, target,
             AlertStatus.sent if ok else AlertStatus.failed, "email send")
        return "sent" if ok else "failed"
    elif channel == Channel.sms:
        if not user.phone_verified or not user.phone_number:
            _log(db, user, sub, channel, atype, target, AlertStatus.skipped, "phone not verified")
            return "skipped"
        ok = send_sms(user.phone_number, f"SubTrack: {sub.merchant_name} {label} on {target.isoformat()}.")
        _log(db, user, sub, channel, atype, target,
             AlertStatus.sent if ok else AlertStatus.failed, "sms send")
        return "sent" if ok else "failed"
    return "noop"


@celery_app.task(name="app.tasks.alert_tasks.send_daily_alerts")
def send_daily_alerts() -> dict:
    db = SessionLocal()
    sent = skipped = 0
    try:
        today = dt.date.today()
        # Only users who actually have alerts enabled; load their preferences in
        # the same query (avoids the old per-user lookup / N+1). Use the enum
        # value rather than a bare string for the status filter.
        users = (
            db.query(User)
            .join(AlertPreference, User.id == AlertPreference.user_id)
            .options(joinedload(User.alert_preferences))
            .filter(
                (AlertPreference.email_alerts == True)  # noqa: E712
                | (AlertPreference.sms_alerts == True)  # noqa: E712
            )
            .all()
        )
        for user in users:
            prefs = user.alert_preferences
            subs = db.query(Subscription).filter(
                Subscription.user_id == user.id,
                Subscription.status != SubStatus.cancelled,
            ).all()
            for sub in subs:
                for days in WINDOWS:
                    target = today + dt.timedelta(days=days)
                    if sub.trial_end_date == target and prefs.email_alerts:
                        res = _send_channel(db, user, sub, Channel.email, AlertType.trial_end, target)
                        if res == "skipped":
                            skipped += 1
                        elif res in ("sent", "failed"):
                            sent += 1
                    if sub.next_renewal_date == target and prefs.email_alerts:
                        res = _send_channel(db, user, sub, Channel.email, AlertType.renewal, target)
                        if res == "skipped":
                            skipped += 1
                        elif res in ("sent", "failed"):
                            sent += 1
                    if sub.trial_end_date == target and prefs.sms_alerts and user.phone_verified:
                        res = _send_channel(db, user, sub, Channel.sms, AlertType.trial_end, target)
                        if res == "skipped":
                            skipped += 1
                        elif res in ("sent", "failed"):
                            sent += 1
                    if sub.next_renewal_date == target and prefs.sms_alerts and user.phone_verified:
                        res = _send_channel(db, user, sub, Channel.sms, AlertType.renewal, target)
                        if res == "skipped":
                            skipped += 1
                        elif res in ("sent", "failed"):
                            sent += 1
    finally:
        db.close()
    return {"sent_attempts": sent, "skipped": skipped}


@celery_app.task(name="app.tasks.alert_tasks.send_test_alert")
def send_test_alert(user_id: int, subscription_id: int) -> bool:
    """On-demand test email used by the end-to-end demo."""
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        sub = db.get(Subscription, subscription_id)
        if not user or not sub:
            return False
        subject = f"[SubTrack] Test alert for {sub.merchant_name}"
        body = (
            f"Hello {user.email},\n\nThis is a TEST alert from SubTrack.\n"
            f"Subscription: {sub.merchant_name}\n"
            f"Amount: {sub.amount} {sub.currency}\n"
            f"Billing: {sub.billing_cycle}\nStatus: {sub.status}\n\n— SubTrack"
        )
        _throttle()
        ok = send_email(user.email, subject, body)
        _log(db, user, sub, Channel.email, AlertType.renewal, dt.date.today(),
             AlertStatus.sent if ok else AlertStatus.failed, "test alert")
        return ok
    finally:
        db.close()
