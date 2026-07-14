"""Gmail ingestion HTTP routes (Phase 2, feature-flagged).

Exposes the previously-unreachable ingestion client so the mobile app can:
  GET  /api/gmail/connect        -> returns Google consent URL (opens in browser)
  GET  /api/gmail/oauth2callback  -> Google redirects here; stores token; returns to app
  GET  /api/gmail/status         -> is Gmail connected + is the AI pipeline enabled?
  POST /api/gmail/ingest         -> scan inbox, classify, create subscriptions (source=gmail)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from ..auth.google_oauth import is_configured as google_configured
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..gmail import client as gmail
from ..models import EncryptedOAuthToken, Subscription, User

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


def _frontend_url(path: str = "") -> str:
    return f"{settings.app_url.rstrip('/')}{path}"


@router.get("/connect")
def connect(user: User = Depends(get_current_user)):
    if not google_configured():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured (set google_oauth client_id/secret).",
        )
    url = gmail.build_consent_url(state=f"u{user.id}")
    return JSONResponse({"url": url})


@router.get("/oauth2callback")
def oauth2callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        uid = int(state.replace("u", ""))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        gmail.exchange_and_store(db, user, code)
    except Exception as exc:  # surface a friendly error back in the app
        return RedirectResponse(_frontend_url(f"/?gmail=error&reason={exc}"))
    return RedirectResponse(_frontend_url("/?gmail=connected"))


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    connected = (
        db.query(EncryptedOAuthToken)
        .filter_by(user_id=user.id, provider="google")
        .first()
        is not None
    )
    return {
        "connected": connected,
        "gmail_enabled": gmail.gmail_enabled(),
        "openrouter_configured": bool(settings.openrouter_api_key),
    }


@router.post("/ingest")
def ingest(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not gmail.gmail_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail integration is disabled or OpenRouter key is missing.",
        )
    if not db.query(EncryptedOAuthToken).filter_by(user_id=user.id, provider="google").first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect Gmail first.")
    created = gmail.ingest(db, user)
    return {"created": created}
