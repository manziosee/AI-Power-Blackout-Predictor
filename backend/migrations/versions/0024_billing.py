"""0024 billing tables subscription plans user subscriptions billing events

Revision ID: 0024
Revises: 0023
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_PG = None


def _is_pg():
    global _PG
    if _PG is None:
        bind = op.get_bind()
        _PG = bind.dialect.name == "postgresql"
    return _PG


def _uuid_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import UUID
        return UUID(as_uuid=True)
    return sa.String(36)


def _jsonb_col():
    if _is_pg():
        from sqlalchemy.dialects.postgresql import JSONB
        return JSONB()
    return sa.Text()


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("price_usd_monthly", sa.Float(), nullable=False, server_default="0"),
        sa.Column("price_usd_yearly", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_locations", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_alert_subscriptions", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("sms_alerts_per_month", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("api_access", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("webhook_access", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("white_label", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("data_export", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("stripe_monthly_price_id", sa.String(100), nullable=True),
        sa.Column("stripe_yearly_price_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_subscriptions",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("user_id", _uuid_col(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", _uuid_col(), sa.ForeignKey("subscription_plans.id"), nullable=False),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])

    op.create_table(
        "billing_events",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("user_id", _uuid_col(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stripe_event_id", sa.String(100), nullable=True, unique=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("payload", _jsonb_col(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("billing_events")
    op.drop_table("user_subscriptions")
    op.drop_table("subscription_plans")
