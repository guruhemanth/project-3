# SubTrack — Architecture (Blueprint phase)

## High-level components
```
Browser (React+TS+Tailwind)
        │  HTTPS / JSON
        ▼
FastAPI (port 8000)  ── auth (JWT) ── SQLAlchemy ── PostgreSQL
        │                                        │
        │ Celery (beat schedule + worker)        │
        ├──► Valkey (broker/backend) ◄───────────┘
        │
        ├──► Email channel: SendGrid API  OR  SMTP→MailHog (dev)
        ├──► SMS channel:   Twilio API     (skipped if no creds)
        └──► AlertLog table (dedup per channel/date)

Phase 2 (feature-flagged): Gmail OAuth2 (gmail.readonly) → inbox scan →
Anthropic LLM classification → Subscription rows (source=gmail).
```

## Directory layout (under project-3)
```
plan/          requirements, assumptions
blueprint/     architecture, data model, API design, Gmail system prompt
code/backend/  FastAPI app (app/), alembic/, main entry
code/frontend/ React+TS+Tailwind app
build/         requirements.txt, alembic.ini
test/          pytest + e2e script
run/           start.sh, e2e demo
credentials.yaml
```

## Build order (this session)
1. Auth (register/login/JWT; Google OAuth stub) — no phone at signup.
2. Subscription CRUD (fields per spec) + calendar feed.
3. Dashboard data (list w/ sort+filter, calendar dates).
4. Alert preferences (email default ON, sms default OFF; warning if both OFF;
   SMS enable → phone + OTP).
5. Alert system (Celery beat daily; windows [7,3,1]; per-channel send; AlertLog dedup).
6. Gmail integration — system prompt shown; implementation behind feature flag (Phase 2).

## Security controls
- Passwords: bcrypt via passlib.
- JWT: HS256, secret from env/credentials, 1440-min expiry.
- OAuth tokens at rest: Fernet encryption, key from `FERNET_KEY`.
- Raw email bodies: never persisted beyond the parsing job's lifetime (Phase 2).
- Rate limiting: per-IP token bucket on all public endpoints + alert job.
- Gmail scope: minimum `gmail.readonly` only; any broader scope requires explicit ask.
