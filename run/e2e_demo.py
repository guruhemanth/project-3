"""End-to-end demo: manual create -> dashboard list -> Celery test alert email.

Run from project root after services are up:
    cd code/backend && alembic upgrade head
    python ../../run/e2e_demo.py

Uses FastAPI TestClient (no running uvicorn needed) and calls the Celery task
function directly (synchronous). Email is delivered to MailHog (localhost:1025)
and verified via its HTTP API (localhost:8025).
"""
import os
import sys
import time
import json
import shutil
import socket
import subprocess
import urllib.request

# --- paths / env ---
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "code", "backend")
sys.path.insert(0, BACKEND)
os.environ.setdefault("SUBTRACK_CREDENTIALS_PATH", os.path.join(ROOT, "credentials.yaml"))
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "1")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import User, Subscription  # noqa: E402
from app.tasks.alert_tasks import send_test_alert  # noqa: E402

MAILHOG_API = "http://localhost:8025/api/v2/messages"
UNIQ = os.urandom(3).hex()
EMAIL = f"e2e_{UNIQ}@subtrack.com"

_mailhog_proc = None


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    s = socket.socket()
    s.settimeout(1)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def ensure_mailhog():
    """Start MailHog as a child process so it lives for this run (the tool reaps
    detached background processes between commands)."""
    global _mailhog_proc
    if _port_open(1025):
        return
    binpath = shutil.which("mailhog") or "/usr/local/bin/mailhog"
    if not os.path.exists(binpath):
        print("   [warn] mailhog binary not found; email step will be skipped")
        return
    # Use MailHog defaults (SMTP :1025, UI :8025) to avoid a double UI bind.
    _mailhog_proc = subprocess.Popen(
        [binpath],
        stdout=open("/tmp/mailhog_e2e.log", "w"),
        stderr=subprocess.STDOUT,
    )
    for _ in range(20):
        if _port_open(1025):
            break
        time.sleep(0.5)
    print(f"   mailhog started (pid={_mailhog_proc.pid}, port1025_open={_port_open(1025)})")


def stop_mailhog():
    global _mailhog_proc
    if _mailhog_proc and _mailhog_proc.poll() is None:
        _mailhog_proc.terminate()


def _mailhog_count(recipient: str) -> int:
    try:
        with urllib.request.urlopen(MAILHOG_API, timeout=5) as r:
            msgs = json.loads(r.read()).get("items", [])
        return sum(1 for m in msgs if recipient in (m.get("Content", {}).get("Headers", {}).get("To", [])))
    except Exception:
        return -1


def main():
    ensure_mailhog()
    client = TestClient(app)
    print("== 1. Register user ==")
    r = client.post("/api/auth/register", json={"email": EMAIL, "password": "password123"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/auth/me", headers=h).json()
    print(f"   user id={me['id']} email={me['email']}")

    print("== 2. Create subscription manually ==")
    payload = {
        "merchant_name": "Spotify", "amount": 9.99, "currency": "USD",
        "billing_cycle": "monthly", "status": "trial",
        "trial_end_date": "2026-08-10", "notes": "music",
    }
    r = client.post("/api/subscriptions", json=payload, headers=h)
    assert r.status_code == 201, r.text
    sub = r.json()
    print(f"   created sub id={sub['id']} merchant={sub['merchant_name']}")

    print("== 3. Dashboard list shows it ==")
    r = client.get("/api/subscriptions", headers=h)
    assert r.status_code == 200
    subs = r.json()
    assert any(s["id"] == sub["id"] for s in subs), "subscription missing from list"
    print(f"   list contains {len(subs)} subscription(s); target present ✅")

    print("== 4. Celery job sends a test alert email ==")
    ok = send_test_alert(me["id"], sub["id"])
    print(f"   send_test_alert returned: {ok}")

    print("== 5. Verify email received by MailHog ==")
    received = False
    for _ in range(10):
        cnt = _mailhog_count(EMAIL)
        if cnt > 0:
            received = True
            break
        time.sleep(0.5)
    if received:
        print(f"   ✅ Email delivered to {EMAIL} (verified via MailHog API)")
    else:
        print(f"   ⚠️  Email not observed in MailHog for {EMAIL} (count={_mailhog_count(EMAIL)})")

    print("\n=== E2E RESULT ===")
    print("create -> dashboard -> celery alert email:",
          "PASS ✅" if (ok and received) else "PARTIAL ⚠️")
    print("Check the inbox at http://localhost:8025")
    stop_mailhog()


if __name__ == "__main__":
    main()
