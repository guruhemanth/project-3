"""Gmail ingestion client (Phase 2, feature-flagged).

Minimum OAuth2 scope only: `gmail.readonly`. Raw email bodies are processed in-memory
and NEVER persisted beyond the lifetime of this job. Requires `feature_flags.gmail_integration`
to be true and an OpenRouter API key for classification.
"""
from __future__ import annotations

import base64
import json
import os
from email import message_from_bytes

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import EncryptedOAuthToken, Subscription, SubSource, User
from ..security import decrypt_token, encrypt_token
from .system_prompt import GMAIL_SYSTEM_PROMPT, user_prompt

GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1"
SCOPES = "https://www.googleapis.com/auth/gmail.readonly"  # MINIMUM required


def gmail_enabled() -> bool:
    # Enabled when the feature flag is on and the OpenRouter LLM provider is configured.
    return bool(settings.gmail_integration) and bool(settings.openrouter_api_key)


def build_consent_url(state: str = "subtrack-gmail") -> str:
    from urllib.parse import urlencode

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.gmail_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GMAIL_AUTH_URL}?{urlencode(params)}"


def exchange_and_store(db: Session, user: User, code: str) -> None:
    data = {
        "code": code, "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri, "grant_type": "authorization_code",
    }
    r = httpx.post(GMAIL_TOKEN_URL, data=data, timeout=10)
    r.raise_for_status()
    token_json = r.json()
    enc = EncryptedOAuthToken(
        user_id=user.id, provider="google",
        encrypted_token=encrypt_token(json.dumps(token_json)),
    )
    db.add(enc)
    db.commit()


def _get_access_token(db: Session, user: User) -> str | None:
    tok = db.query(EncryptedOAuthToken).filter_by(user_id=user.id, provider="google").first()
    if not tok:
        return None
    raw = json.loads(decrypt_token(tok.encrypted_token) or "{}")
    return raw.get("access_token")


def _decode_body(payload: dict) -> str:
    data = payload.get("body", {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data + "===").decode("utf-8", "ignore")
    return ""


def fetch_billing_candidates(db: Session, user: User, max_results: int = 20) -> list[dict]:
    token = _get_access_token(db, user)
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    # Heuristic query for billing-like mail.
    q = "subject:(receipt OR invoice OR subscription OR billing OR payment) newer_than:30d"
    r = httpx.get(f"{GMAIL_API}/users/me/messages", headers=headers,
                  params={"q": q, "maxResults": max_results}, timeout=15)
    r.raise_for_status()
    out = []
    for m in r.json().get("messages", []):
        mr = httpx.get(f"{GMAIL_API}/users/me/messages/{m['id']}", headers=headers, timeout=15)
        msg = mr.json()
        # Raw body is used in-memory only; never persisted.
        body = _decode_body(msg.get("payload", {}))
        out.append({"id": m["id"], "snippet": msg.get("snippet", ""), "body": body[:2000]})
    return out


def _extract_json(text: str) -> dict:
    """Parse the model's reply into a dict, tolerating stray code fences/prose."""
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` fences if the model added them
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _classify_openrouter(excerpt: str, sender: str, subject: str) -> dict:
    """Classify a billing email via OpenRouter (OpenAI-compatible chat API)."""
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        # Optional attribution headers recommended by OpenRouter.
        "HTTP-Referer": "https://subtrack.app",
        "X-Title": "SubTrack",
    }
    payload = {
        "model": settings.openrouter_model,
        "max_tokens": 300,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": GMAIL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt(sender, subject, excerpt)},
        ],
    }
    r = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers=headers, json=payload, timeout=30,
    )
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return _extract_json(content)


def classify(excerpt: str, sender: str, subject: str) -> dict:
    """Extract subscription fields from a billing email via OpenRouter."""
    if not settings.openrouter_api_key:
        raise RuntimeError("No LLM provider configured (set openrouter.api_key in credentials.yaml)")
    return _classify_openrouter(excerpt, sender, subject)


def ingest(db: Session, user: User) -> int:
    """Scan inbox, classify, and create Subscription rows (source=gmail)."""
    created = 0
    for mail in fetch_billing_candidates(db, user):
        try:
            parsed = classify(mail["body"], sender="", subject=mail["snippet"])
        except Exception:
            continue
        if not parsed.get("merchant") or not parsed.get("amount"):
            continue
        sub = Subscription(
            user_id=user.id,
            merchant_name=parsed["merchant"],
            amount=parsed["amount"],
            currency=parsed.get("currency") or "USD",
            billing_cycle=parsed.get("billing_cycle") or "monthly",
            status=parsed.get("status") or "paid",
            source=SubSource.gmail,
        )
        db.add(sub)
        created += 1
    db.commit()
    return created
