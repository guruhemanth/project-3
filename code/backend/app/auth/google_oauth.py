"""Google OAuth2 helpers (minimum scope: openid email profile).

The flow is fully implemented but disabled until GOOGLE_CLIENT_ID / SECRET are set
in credentials.yaml (the endpoints return 501 otherwise). Gmail scope is NEVER
requested here — that is a separate, feature-flagged Phase 2 concern.
"""
from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from ..config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES = "openid email profile"


def is_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def build_authorization_url(state: str = "subtrack") -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    from urllib.parse import urlencode

    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange code for userinfo (email + google sub). Raises on failure."""
    if not is_configured():
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="Google OAuth is not configured")
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        r = httpx.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
        r.raise_for_status()
        access_token = r.json()["access_token"]
        ui = httpx.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        ui.raise_for_status()
        info = ui.json()
        return {"email": info.get("email"), "sub": info.get("sub"), "verified": info.get("email_verified", False)}
    except httpx.HTTPError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Google OAuth exchange failed: {e}")
