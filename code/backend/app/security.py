"""Security primitives: password hashing, JWT, Fernet encryption, OTP."""
from __future__ import annotations

import base64
import os
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Passwords -------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(password, hashed)


# --- JWT -------------------------------------------------------------------
def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "iat": datetime.now(timezone.utc), "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


# --- Fernet (encrypt OAuth tokens at rest) ----------------------------------
def _fernet() -> Fernet:
    key = settings.fernet_key
    if not key:
        # Derive a stable dev key from secret_key so restarts don't break decryption.
        key = base64.urlsafe_b64encode(settings.secret_key.encode().ljust(32, b"0")[:32])
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_token(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


# --- OTP -------------------------------------------------------------------
def generate_otp(length: int = 6) -> str:
    # Use the `secrets` module (cryptographically strong) rather than a raw
    # single-byte modulo which is less uniform and less clearly intentional.
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(otp: str) -> str:
    return pwd_context.hash(otp)


def verify_otp(otp: str, otp_hash: str | None) -> bool:
    if not otp_hash:
        return False
    return pwd_context.verify(otp, otp_hash)
