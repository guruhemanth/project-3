"""API smoke tests (pytest) using FastAPI TestClient against the real Postgres DB."""
import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code", "backend"))
os.environ.setdefault("SUBTRACK_CREDENTIALS_PATH",
                      os.path.join(os.path.dirname(__file__), "..", "credentials.yaml"))

from app.main import app  # noqa: E402

client = TestClient(app)
UNIQ = os.urandom(3).hex()


def _register():
    # Fresh unique email per call so tests don't collide (DB is shared/persistent).
    email = f"test_{os.urandom(4).hex()}@subtrack.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return email, r.json()["access_token"]


def test_register_login_me():
    email, token = _register()
    # login works
    r = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200 and "access_token" in r.json()
    # /me works with token
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == email
    assert r.json()["has_password"] is True


def test_subscription_crud_and_list():
    _, token = _register()
    h = {"Authorization": f"Bearer {token}"}
    payload = {
        "merchant_name": "Netflix", "amount": 15.99, "currency": "USD",
        "billing_cycle": "monthly", "status": "paid",
        "next_renewal_date": "2026-08-01", "notes": "streaming",
    }
    r = client.post("/api/subscriptions", json=payload, headers=h)
    assert r.status_code == 201, r.text
    sub_id = r.json()["id"]
    # list shows it (dashboard data source)
    r = client.get("/api/subscriptions", headers=h)
    assert r.status_code == 200
    ids = [s["id"] for s in r.json()]
    assert sub_id in ids
    # filter by status
    r = client.get("/api/subscriptions?status=paid", headers=h)
    assert all(s["status"] == "paid" for s in r.json())
    # calendar includes it
    r = client.get("/api/subscriptions/calendar", headers=h)
    assert r.status_code == 200
    # update
    r = client.put(f"/api/subscriptions/{sub_id}", json={"status": "cancelled"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    # delete
    r = client.delete(f"/api/subscriptions/{sub_id}", headers=h)
    assert r.status_code == 204


def test_default_alert_preferences():
    _, token = _register()
    r = client.get("/api/alerts/preferences", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # email default ON, sms default OFF, no phone
    assert r.json()["email_alerts"] is True
    assert r.json()["sms_alerts"] is False
    assert r.json()["phone_number"] is None


def test_rate_limit_headers_present():
    _, token = _register()
    r = client.get("/api/subscriptions", headers={"Authorization": f"Bearer {token}"})
    assert "X-RateLimit-Limit" in r.headers


def test_phone_required_before_sms_alerts():
    _, token = _register()
    h = {"Authorization": f"Bearer {token}"}
    # enabling SMS without verified phone -> 400
    r = client.put("/api/alerts/preferences", json={"sms_alerts": True}, headers=h)
    assert r.status_code == 400
