"""enterprise — utility companies, business profiles, webhooks

Revision ID: 0005
Revises: 0001
Create Date: 2026-05-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── utility_companies ─────────────────────────────────────────────────────
    op.create_table(
        "utility_companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country_code", sa.String(5), nullable=False),
        sa.Column("service_area_h3_cells", JSONB, nullable=True),
        sa.Column("api_key", sa.String(60), unique=True, nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("plan", sa.String(20), server_default="trial"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_utility_api_key", "utility_companies", ["api_key"])
    op.create_index("idx_utility_country", "utility_companies", ["country_code"])

    # ── business_profiles ─────────────────────────────────────────────────────
    op.create_table(
        "business_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("business_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("monthly_revenue_usd", sa.Float(), nullable=True),
        sa.Column("employees", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_biz_user", "business_profiles", ["user_id"])
    op.create_index("idx_biz_h3", "business_profiles", ["h3_index"])

    # ── webhook_subscriptions ─────────────────────────────────────────────────
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(60), nullable=False),
        sa.Column("threshold_probability", sa.Float(), server_default="0.70"),
        sa.Column("events", JSONB, server_default='["prediction_threshold","outage_confirmed"]'),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_webhook_user", "webhook_subscriptions", ["user_id"])

    # ── webhook_events ────────────────────────────────────────────────────────
    op.create_table(
        "webhook_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("attempt", sa.Integer(), server_default="1"),
        sa.Column("success", sa.Boolean(), server_default="false"),
        sa.Column("fired_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("idx_webhook_events_sub", "webhook_events", ["subscription_id", "fired_at"])


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("webhook_subscriptions")
    op.drop_table("business_profiles")
    op.drop_table("utility_companies")
