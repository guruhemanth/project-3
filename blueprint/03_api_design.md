# SubTrack — API Design (Blueprint phase)

Base path: `/api`. Auth: `Authorization: Bearer <JWT>` (except public register/login).

## Auth  (`/api/auth`)
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/register` | public | email+password → user (no phone) + JWT |
| POST | `/login` | public | email+password → JWT |
| GET  | `/me` | user | current user profile |
| GET  | `/google/login` | public | redirect to Google consent (501 if unconfigured) |
| GET  | `/google/callback` | public | OAuth code exchange → JWT |
| POST | `/phone/request-otp` | user | start phone verification (SMS or log) |
| POST | `/phone/verify-otp` | user | complete phone verification |

## Subscriptions (`/api/subscriptions`)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/` | create (manual/gmail) |
| GET  | `/` | list; `?status=`, `?billing_cycle=`, `?sort=next_renewal_date\|merchant_name\|amount\|status`, `?order=asc\|desc` |
| GET  | `/calendar` | upcoming trial_end & renewal dates (for calendar view) |
| GET  | `/{id}` | get one (owner only) |
| PUT  | `/{id}` | update |
| DELETE | `/{id}` | delete |

## Alert preferences (`/api/alerts`)
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/preferences` | current toggles |
| PUT  | `/preferences` | set `email_alerts` / `sms_alerts` (enabling sms requires verified phone) |

## Alert system (internal / Celery)
- `send_daily_alerts()` — beat schedule, daily. Windows `[7,3,1]` days.
- `send_test_alert(user_id, subscription_id)` — immediate test email (e2e).
- Email via SendGrid API or SMTP→MailHog; SMS via Twilio. Results → `alert_logs`.

## Rate limiting
- Middleware: per-IP token bucket (Redis/Valkey; in-memory fallback).
  Public endpoints stricter; alert job throttled internally.
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` on 429.
