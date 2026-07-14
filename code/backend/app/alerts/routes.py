"""Alert preference routes (Settings page backend)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AlertPreference, User
from ..schemas import AlertPreferencesOut, AlertPreferencesUpdate

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _get_or_create_prefs(db: Session, user: User) -> AlertPreference:
    prefs = db.query(AlertPreference).filter(AlertPreference.user_id == user.id).first()
    if not prefs:
        prefs = AlertPreference(user_id=user.id, email_alerts=True, sms_alerts=False)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.get("/preferences", response_model=AlertPreferencesOut)
def get_prefs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = _get_or_create_prefs(db, user)
    return AlertPreferencesOut(
        email_alerts=prefs.email_alerts,
        sms_alerts=prefs.sms_alerts,
        phone_verified=user.phone_verified,
        phone_number=user.phone_number,
    )


@router.put("/preferences", response_model=AlertPreferencesOut)
def update_prefs(payload: AlertPreferencesUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = _get_or_create_prefs(db, user)
    if payload.email_alerts is not None:
        prefs.email_alerts = payload.email_alerts
    if payload.sms_alerts is not None:
        if payload.sms_alerts and not user.phone_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot enable SMS alerts: verify a phone number first (POST /api/auth/phone/request-otp).",
            )
        prefs.sms_alerts = payload.sms_alerts
    db.commit()
    db.refresh(prefs)
    return AlertPreferencesOut(
        email_alerts=prefs.email_alerts,
        sms_alerts=prefs.sms_alerts,
        phone_verified=user.phone_verified,
        phone_number=user.phone_number,
    )
