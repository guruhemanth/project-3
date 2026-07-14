"""Application configuration.

Loads secrets from ``credentials.yaml`` (generated at setup) and exposes them as a
single :class:`Settings` object. Environment variables take precedence where useful.
All sensitive values (DB password, JWT secret, Fernet key) live in credentials.yaml
and are NEVER committed.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel


def _find_project_root() -> Path:
    p = Path(__file__).resolve().parent
    for _ in range(6):
        if (p / "credentials.yaml").exists():
            return p
        p = p.parent
    # fallback: project-3 (code/backend/app -> 4 levels up)
    return Path(__file__).resolve().parent.parent.parent.parent


PROJECT_ROOT = _find_project_root()


class Settings(BaseModel):
    # database
    database_url: str
    # redis / valkey
    redis_url: str = "redis://localhost:6379/0"
    # auth / crypto
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    fernet_key: str = ""
    secret_key: str = ""
    # mail (local SMTP catch-all)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    # sendgrid (production email path)
    sendgrid_api_key: str = ""
    from_email: str = "noreply@subtrack.local"
    # twilio (sms)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    # google oauth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""
    gmail_redirect_uri: str = "http://localhost:8000/api/gmail/oauth2callback"
    # app (frontend) origin for OAuth redirects
    app_url: str = "http://localhost:5173"
    # openrouter (LLM provider for gmail classification)
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # feature flags
    gmail_integration: bool = False
    # cors
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


def _load() -> Settings:
    path = os.environ.get("SUBTRACK_CREDENTIALS_PATH") or str(PROJECT_ROOT / "credentials.yaml")
    data: dict = {}
    if Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    def g(section: str, key: str, default=None):
        return (data.get(section) or {}).get(key, default)

    pg = data.get("postgres") or {}
    database_url = (
        f"postgresql+psycopg2://{pg.get('user')}:{pg.get('password')}"
        f"@{pg.get('host','localhost')}:{pg.get('port',5432)}/{pg.get('database')}"
    )

    return Settings(
        database_url=os.environ.get("SUBTRACK_DATABASE_URL", database_url),
        redis_url=os.environ.get("SUBTRACK_REDIS_URL", g("valkey", "url", "redis://localhost:6379/0")),
        jwt_secret=os.environ.get("SUBTRACK_JWT_SECRET", g("backend", "jwt_secret", "dev-secret")),
        jwt_algorithm=g("backend", "jwt_algorithm", "HS256"),
        access_token_expire_minutes=g("backend", "access_token_expire_minutes", 1440),
        fernet_key=os.environ.get("SUBTRACK_FERNET_KEY", g("backend", "fernet_key", "")),
        secret_key=os.environ.get("SUBTRACK_SECRET_KEY", g("backend", "secret_key", "")),
        smtp_host=g("mailhog", "smtp_host", "localhost"),
        smtp_port=int(g("mailhog", "smtp_port", 1025)),
        sendgrid_api_key=os.environ.get("SENDGRID_API_KEY", g("sendgrid", "api_key", "")),
        from_email=g("sendgrid", "from_email", "noreply@subtrack.local"),
        twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID", g("twilio", "account_sid", "")),
        twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN", g("twilio", "auth_token", "")),
        twilio_from_number=os.environ.get("TWILIO_FROM_NUMBER", g("twilio", "from_number", "")),
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID", g("google_oauth", "client_id", "")),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", g("google_oauth", "client_secret", "")),
        google_redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI", g("google_oauth", "redirect_uri", "")),
        gmail_redirect_uri=os.environ.get("GMAIL_REDIRECT_URI", g("google_oauth", "gmail_redirect_uri", "http://localhost:8000/api/gmail/oauth2callback")),
        app_url=os.environ.get("SUBTRACK_APP_URL", g("feature_flags", "app_url", "http://localhost:5173")),
        openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", g("openrouter", "api_key", "")),
        openrouter_model=os.environ.get("OPENROUTER_MODEL", g("openrouter", "model", "openai/gpt-oss-120b:free")),
        openrouter_base_url=os.environ.get("OPENROUTER_BASE_URL", g("openrouter", "base_url", "https://openrouter.ai/api/v1")),
        gmail_integration=bool(os.environ.get("SUBTRACK_GMAIL", g("feature_flags", "gmail_integration", False))),
        cors_origins=os.environ.get("SUBTRACK_CORS", "http://localhost:5173,http://localhost:3000").split(","),
    )


settings = _load()
