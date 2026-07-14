# SubTrack — Subscription Tracking SaaS

A subscription tracker: auth, subscription CRUD, dashboard (list + calendar),
alert preferences, scheduled alert emails/SMS, and an optional Gmail ingestion
feature (Phase 2, behind a flag).

Built per the requested methodology: **plan → blueprint → code → build → test → run**.

## Stack
- **Backend:** Python 3.11 + FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL 18
- **Frontend:** React 18 + TypeScript + Tailwind (Vite)
- **Jobs:** Celery + Valkey (Redis-compatible) broker/backend
- **Email:** SendGrid API in prod, local SMTP (MailHog) in dev
- **No Docker** (explicit requirement) — services run natively.

## Layout
```
plan/        requirements, assumptions
blueprint/   architecture, data model, API design, Gmail system prompt
code/backend/ FastAPI app (app/), alembic/, alembic.ini
code/frontend/ React+TS+Tailwind app
build/       requirements.txt
test/        pytest API smoke tests
run/         start.sh (full stack), e2e_demo.py
credentials.yaml
```

## Quick start (this machine)
Services already provisioned during setup: Postgres (:5432), Valkey (:6379),
MailHog (:1025 SMTP / :8025 UI). Activate the venv and run:
```bash
source .venv/bin/activate
export PYTHONPATH=$PWD/code/backend SUBTRACK_CREDENTIALS_PATH=$PWD/credentials.yaml
cd code/backend && alembic upgrade head && cd ../..
bash run/start.sh            # starts API + Celery + frontend
python run/e2e_demo.py      # end-to-end: create -> dashboard -> test alert email
pytest test/                # API tests
```

## Credentials
All secrets live in `credentials.yaml` (auto-generated). External provider keys
(SendGrid, Twilio, Google, Anthropic) are placeholders — fill them to enable the
corresponding features. The app degrades gracefully (MailHog for email, logged SMS).

## Feature phases
- **Phase 1 (this session):** auth (JWT + Google OAuth stub), subscription CRUD,
  dashboard list + calendar, alert preferences, scheduled Celery alert job with
  per-channel dedup (`alert_logs`).
- **Phase 2 (optional, flag-gated):** Gmail ingestion via `gmail.readonly` OAuth
  + Anthropic classification. See `blueprint/04_gmail_system_prompt.md` for the
  exact system prompt. Disabled by default (`feature_flags.gmail_integration`).

## Security notes
- Passwords: bcrypt. JWT: HS256. OAuth tokens: Fernet-encrypted at rest.
- Rate limiting: per-IP token bucket on all public endpoints + throttled alert job.
- Minimum Gmail scope (`gmail.readonly`); raw email bodies never persisted.
