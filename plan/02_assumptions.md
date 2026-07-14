# SubTrack — Assumptions & Clarifications (Plan phase)

The original spec asked to confirm the auth provider, alert-channel provider, and
deployment target before starting. Per the spec these are already specified; the only
deviation is the "do not use Docker" instruction. Decisions made:

## Auth provider — CONFIRMED as specified
- Email/password (JWT sessions) + Google OAuth sign-in.
- Email is required at signup; **phone number is NOT collected at signup**.
- Phone is requested only when the user enables "SMS alerts" (with OTP verification).
- Google OAuth client_id/secret are placeholders in `credentials.yaml`; the flow is
  fully implemented but returns `501 Not Implemented` until real creds are supplied.

## Alert-channel provider — CONFIRMED as specified
- Email via **SendGrid** API; SMS via **Twilio**.
- For the local end-to-end test we route email through **SMTP → MailHog** so a real
  message is sent/received without a SendGrid key. Production path uses SendGrid when
  `SENDGRID_API_KEY` is set.

## Deployment target — CHANGED per user instruction
- Spec said Docker Compose (local) + Fly.io (prod). User said **do not use Docker**.
- Local run uses native services (Postgres, Valkey, MailHog) started as processes.
- Fly.io remains the documented production target; no `Dockerfile` is produced.

## Other assumptions
- Currency stored as ISO-4217 code string (e.g. `USD`); amount as `NUMERIC(12,2)`.
- `trial_end_date` / `next_renewal_date` are dates (no timezone needed for renewal day).
- Alert windows are exactly the days `[7, 3, 1]` before the relevant date.
- Duplicate prevention: one `AlertLog` row per (subscription, channel, alert_type, date).
- Rate limiting uses Redis (Valkey) token-bucket per IP; in-memory fallback if Redis down.
- The "dashboard shows it" end-to-end check is validated via the API list endpoint that
  feeds the dashboard (frontend reads the same endpoint); a manual UI smoke test is also
  provided via `run/start.sh`.

## Open items for the user (non-blocking)
1. Provide Google OAuth client_id/secret to enable "Sign in with Google".
2. Provide SendGrid API key (or keep MailHog for dev email).
3. Provide Twilio creds to actually send SMS (otherwise SMS is logged/skipped).
4. Provide Anthropic API key + enable `feature_flags.gmail_integration` for Phase 2.
