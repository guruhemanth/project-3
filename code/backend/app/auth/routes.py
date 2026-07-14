"""Auth routes: register, login, me, Google OAuth, phone OTP verification."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AlertPreference, User
from ..schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
    RequestOtpRequest,
    VerifyOtpRequest,
)
from ..security import (
    create_access_token,
    generate_otp,
    hash_otp,
    hash_password,
    verify_otp,
    verify_password,
)
from ..tasks.sms import send_sms  # local import to avoid heavy deps at startup

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    # Default alert preference: email ON (required at signup), SMS OFF.
    db.add(AlertPreference(user_id=user.id, email_alerts=True, sms_alerts=False))
    db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id, email=user.email, is_email_verified=user.is_email_verified,
        phone_verified=user.phone_verified, has_password=bool(user.hashed_password),
    )


@router.get("/google/login")
def google_login():
    from .google_oauth import is_configured, build_authorization_url

    if not is_configured():
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="Google OAuth is not configured (set client_id/secret in credentials.yaml)")
    return RedirectResponse(build_authorization_url())


@router.get("/google/callback", response_model=TokenResponse)
def google_callback(code: str, db: Session = Depends(get_db)):
    from .google_oauth import exchange_code

    info = exchange_code(code)
    if not info.get("email"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google did not return email")
    user = db.query(User).filter(User.google_sub == info["sub"]).first()
    if not user:
        user = db.query(User).filter(User.email == info["email"]).first()
    if not user:
        user = User(email=info["email"], google_sub=info["sub"], is_email_verified=bool(info.get("verified")))
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(AlertPreference(user_id=user.id, email_alerts=True, sms_alerts=False))
        db.commit()
    else:
        if not user.google_sub:
            user.google_sub = info["sub"]
            db.commit()
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/phone/request-otp")
def request_otp(payload: RequestOtpRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    otp = generate_otp()
    user.phone_number = payload.phone_number
    user.otp_code_hash = hash_otp(otp)
    from datetime import datetime, timedelta, timezone
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.commit()
    # Send via SMS if configured; otherwise log (dev). Never return the OTP.
    send_sms(user.phone_number, f"Your SubTrack verification code is {otp}")
    return {"detail": "Verification code sent"}


@router.post("/phone/verify-otp")
def verify_otp_route(payload: VerifyOtpRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    if user.otp_expires_at and user.otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")
    if not verify_otp(payload.code, user.otp_code_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
    user.phone_verified = True
    user.otp_code_hash = None
    user.otp_expires_at = None
    db.commit()
    return {"detail": "Phone verified", "phone_verified": True}
