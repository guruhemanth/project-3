"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---------------- Auth ----------------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_email_verified: bool
    phone_verified: bool
    has_password: bool

    model_config = {"from_attributes": True}


# ---------------- Phone / OTP ----------------
class RequestOtpRequest(BaseModel):
    phone_number: str = Field(min_length=6, max_length=32)


class VerifyOtpRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


# ---------------- Subscriptions ----------------
class SubscriptionCreate(BaseModel):
    merchant_name: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=8)
    billing_cycle: str  # weekly | monthly | yearly
    status: str = "trial"  # trial | paid | cancelled
    trial_end_date: Optional[date] = None
    next_renewal_date: Optional[date] = None
    notes: Optional[str] = None
    source: str = "manual"  # manual | gmail


class SubscriptionUpdate(BaseModel):
    merchant_name: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    status: Optional[str] = None
    trial_end_date: Optional[date] = None
    next_renewal_date: Optional[date] = None
    notes: Optional[str] = None


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    merchant_name: str
    amount: Decimal
    currency: str
    billing_cycle: str
    status: str
    trial_end_date: Optional[date]
    next_renewal_date: Optional[date]
    notes: Optional[str]
    source: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class CalendarItem(BaseModel):
    subscription_id: int
    merchant_name: str
    kind: str  # trial_end | renewal
    date: date


# ---------------- Alerts ----------------
class AlertPreferencesOut(BaseModel):
    email_alerts: bool
    sms_alerts: bool
    phone_verified: bool
    phone_number: Optional[str]

    model_config = {"from_attributes": True}


class AlertPreferencesUpdate(BaseModel):
    email_alerts: Optional[bool] = None
    sms_alerts: Optional[bool] = None


class AlertLogOut(BaseModel):
    id: int
    channel: str
    alert_type: str
    alert_date: date
    status: str
    detail: Optional[str]
    sent_at: Optional[datetime]

    model_config = {"from_attributes": True}
