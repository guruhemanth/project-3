# SubTrack — Data Model (Blueprint phase)

## Tables
### users
- id BIGSERIAL PK
- email VARCHAR(255) UNIQUE NOT NULL
- hashed_password VARCHAR(255) NULL  (NULL for OAuth-only accounts)
- is_email_verified BOOLEAN DEFAULT FALSE
- google_sub VARCHAR(255) NULL UNIQUE  (Google OAuth subject)
- phone_number VARCHAR(32) NULL  (NOT collected at signup)
- phone_verified BOOLEAN DEFAULT FALSE
- otp_code_hash VARCHAR(255) NULL
- otp_expires_at TIMESTAMPTZ NULL
- created_at / updated_at TIMESTAMPTZ

### subscriptions
- id BIGSERIAL PK
- user_id BIGINT FK -> users.id
- merchant_name VARCHAR(255) NOT NULL
- amount NUMERIC(12,2) NOT NULL
- currency VARCHAR(8) NOT NULL DEFAULT 'USD'
- billing_cycle ENUM('weekly','monthly','yearly') NOT NULL
- status ENUM('trial','paid','cancelled') NOT NULL DEFAULT 'trial'
- trial_end_date DATE NULL
- next_renewal_date DATE NULL
- notes TEXT NULL
- source ENUM('manual','gmail') NOT NULL DEFAULT 'manual'
- created_at / updated_at TIMESTAMPTZ

### alert_preferences
- id BIGSERIAL PK
- user_id BIGINT FK -> users.id UNIQUE
- email_alerts BOOLEAN DEFAULT TRUE   (email required at signup → default ON)
- sms_alerts BOOLEAN DEFAULT FALSE
- created_at / updated_at TIMESTAMPTZ

### alert_logs
- id BIGSERIAL PK
- user_id BIGINT FK
- subscription_id BIGINT FK
- channel ENUM('email','sms') NOT NULL
- alert_type ENUM('trial_end','renewal') NOT NULL
- alert_date DATE NOT NULL            (the target date the alert is about)
- status ENUM('sent','failed','skipped') NOT NULL
- detail TEXT NULL
- sent_at TIMESTAMPTZ
- UNIQUE (subscription_id, channel, alert_type, alert_date)  -- dedup

### encrypted_oauth_tokens   (Phase 2 — Gmail)
- id BIGSERIAL PK
- user_id BIGINT FK
- provider VARCHAR(32) NOT NULL DEFAULT 'google'
- encrypted_token TEXT NOT NULL       (Fernet-encrypted JSON of tokens)
- expires_at TIMESTAMPTZ NULL
- created_at / updated_at TIMESTAMPTZ

## Indexes
- subscriptions(user_id), subscriptions(status), subscriptions(next_renewal_date),
  subscriptions(trial_end_date), alert_logs(subscription_id, channel, alert_type, alert_date).
