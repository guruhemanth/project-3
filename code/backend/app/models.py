"""SQLAlchemy ORM models for SubTrack."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

from .database import Base


def _vals(enum_cls):
    return [m.value for m in enum_cls]


class BillingCycle(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class SubStatus(str, enum.Enum):
    trial = "trial"
    paid = "paid"
    cancelled = "cancelled"


class SubSource(str, enum.Enum):
    manual = "manual"
    gmail = "gmail"


class Channel(str, enum.Enum):
    email = "email"
    sms = "sms"


class AlertType(str, enum.Enum):
    trial_end = "trial_end"
    renewal = "renewal"


class AlertStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # NULL for OAuth-only
    is_email_verified = Column(Boolean, default=False)
    google_sub = Column(String(255), nullable=True, unique=True)
    # Phone is NOT collected at signup; only added when SMS alerts are enabled.
    phone_number = Column(String(32), nullable=True)
    phone_verified = Column(Boolean, default=False)
    otp_code_hash = Column(String(255), nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow)

    # Relationships (no schema change; improve query ergonomics / avoid N+1).
    alert_preferences = relationship(
        "AlertPreference", uselist=False, back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant_name = Column(String(255), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    billing_cycle = Column(SAEnum(BillingCycle, name="billing_cycle", values_callable=_vals), nullable=False)
    status = Column(SAEnum(SubStatus, name="sub_status", values_callable=_vals), nullable=False, default=SubStatus.trial)
    trial_end_date = Column(Date, nullable=True, index=True)
    next_renewal_date = Column(Date, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    source = Column(SAEnum(SubSource, name="sub_source", values_callable=_vals), nullable=False, default=SubSource.manual)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow)

    user = relationship("User", back_populates="subscriptions")


class AlertPreference(Base):
    __tablename__ = "alert_preferences"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    email_alerts = Column(Boolean, default=True)   # email required at signup -> default ON
    sms_alerts = Column(Boolean, default=False)     # default OFF
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow)

    user = relationship("User", back_populates="alert_preferences")


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscription_id = Column(BigInteger, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    channel = Column(SAEnum(Channel, name="channel", values_callable=_vals), nullable=False)
    alert_type = Column(SAEnum(AlertType, name="alert_type", values_callable=_vals), nullable=False)
    alert_date = Column(Date, nullable=False)
    status = Column(SAEnum(AlertStatus, name="alert_status", values_callable=_vals), nullable=False)
    detail = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "channel", "alert_type", "alert_date", name="uq_alert_dedup"
        ),
    )


class EncryptedOAuthToken(Base):
    """Phase 2 (Gmail). Encrypted at rest with Fernet."""
    __tablename__ = "encrypted_oauth_tokens"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(32), default="google")
    encrypted_token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=_utcnow)
