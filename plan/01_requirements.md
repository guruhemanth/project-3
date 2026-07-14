# SubTrack — Requirements & Environment (Plan phase)

## 1. Application requirements (functional)
- Subscription tracking SaaS: auth, subscription CRUD, dashboard (list + calendar),
  alert preferences, scheduled alert jobs, optional Gmail ingestion (phase 2).
- Stack: Python 3.11 + FastAPI, PostgreSQL + SQLAlchemy + Alembic, React + TS + Tailwind,
  Redis/Valkey + Celery for background jobs.
- No Docker (explicit user instruction). Services run natively on Fedora 43 (WSL).

## 2. Software installed on this machine (status: DONE)
| Component | Purpose | Status |
|-----------|---------|--------|
| Python 3.11.15 (venv at `project-3/.venv`) | Backend runtime | ✅ |
| PostgreSQL 18.3 (server + client) | Primary DB | ✅ running on :5432 |
| Valkey 8.1.8 (Redis-compatible) | Celery broker/backend | ✅ running on :6379 (`PONG`) |
| MailHog v1.0.1 | Local SMTP catch-all for email testing | ✅ binary at `/usr/local/bin/mailhog` |
| Node v22.22.2 / npm 10.9.7 | Frontend build | ✅ |
| `subtrack` Postgres role + DB | App database | ✅ (md5 auth, localhost) |

> Redis is not in Fedora 43 repos (license change) → replaced by **Valkey**, a drop-in
> Redis fork. Celery connects via `redis://localhost:6379/0`.

## 3. External SaaS providers (require user-supplied credentials)
These cannot be "installed" locally. Placeholders are written to `credentials.yaml`;
real values must be filled by the user. The code degrades gracefully (local stand-ins)
so the app still runs end-to-end without them.

| Provider | Used for | Local stand-in / fallback |
|----------|----------|---------------------------|
| SendGrid | Transactional email alerts | SMTP → MailHog (`localhost:1025`) when no API key |
| Twilio | SMS alerts | Logged/skipped when no creds |
| Google OAuth | "Sign in with Google" | Flow implemented; disabled until client_id/secret set |
| Anthropic | Gmail email → subscription classification (Phase 2) | Behind `feature_flags.gmail_integration=false` |

## 4. Python packages (see `build/requirements.txt`)
fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, pydantic, pydantic-settings,
python-jose[cryptography], passlib[bcrypt], celery, redis, sendgrid, twilio,
cryptography, python-multipart, httpx, email-validator, anthropic, pytest.

## 5. Credentials
All secrets (DB password, JWT secret, Fernet key) are auto-generated and stored in
`/home/guru/projects/project-3/credentials.yaml`. External provider keys are
placeholders (`REPLACE_WITH_...`).
