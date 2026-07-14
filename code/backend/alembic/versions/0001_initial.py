"""Initial schema: users, subscriptions, alert_preferences, alert_logs, oauth tokens.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("google_sub", sa.String(255), nullable=True),
        sa.Column("phone_number", sa.String(32), nullable=True),
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("otp_code_hash", sa.String(255), nullable=True),
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_sub"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("merchant_name", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("billing_cycle", postgresql.ENUM("weekly", "monthly", "yearly", name="billing_cycle"), nullable=False),
        sa.Column("status", postgresql.ENUM("trial", "paid", "cancelled", name="sub_status"), nullable=False, server_default="trial"),
        sa.Column("trial_end_date", sa.Date(), nullable=True),
        sa.Column("next_renewal_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", postgresql.ENUM("manual", "gmail", name="sub_source"), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_next_renewal_date", "subscriptions", ["next_renewal_date"])
    op.create_index("ix_subscriptions_trial_end_date", "subscriptions", ["trial_end_date"])

    op.create_table(
        "alert_preferences",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sms_alerts", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "alert_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subscription_id", sa.BigInteger(), sa.ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", postgresql.ENUM("email", "sms", name="channel"), nullable=False),
        sa.Column("alert_type", postgresql.ENUM("trial_end", "renewal", name="alert_type"), nullable=False),
        sa.Column("alert_date", sa.Date(), nullable=False),
        sa.Column("status", postgresql.ENUM("sent", "failed", "skipped", name="alert_status"), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("subscription_id", "channel", "alert_type", "alert_date", name="uq_alert_dedup"),
    )
    op.create_index("ix_alert_logs_sub_channel", "alert_logs", ["subscription_id", "channel", "alert_type", "alert_date"])

    op.create_table(
        "encrypted_oauth_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="google"),
        sa.Column("encrypted_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("encrypted_oauth_tokens")
    op.drop_table("alert_logs")
    op.drop_table("alert_preferences")
    op.drop_table("subscriptions")
    op.drop_table("users")
    sa.Enum(name="alert_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="alert_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="channel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="sub_source").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="sub_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="billing_cycle").drop(op.get_bind(), checkfirst=True)
