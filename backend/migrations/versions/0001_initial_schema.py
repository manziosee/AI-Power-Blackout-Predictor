"""initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-05-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions ────────────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── h3_cells ──────────────────────────────────────────────────────────────
    op.create_table(
        "h3_cells",
        sa.Column("h3_index", sa.String(15), primary_key=True),
        sa.Column("center_lat", sa.Numeric(10, 7)),
        sa.Column("center_lng", sa.Numeric(10, 7)),
        sa.Column("country_code", sa.String(5)),
        sa.Column("region", sa.String(100)),
        sa.Column("city", sa.String(100)),
        sa.Column("resolution", sa.Integer(), server_default="8"),
    )

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("phone", sa.String(20), unique=True, nullable=False),
        sa.Column("country_code", sa.String(5), nullable=False),
        sa.Column("language", sa.String(5), server_default="en"),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── user_locations ────────────────────────────────────────────────────────
    op.create_table(
        "user_locations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), sa.ForeignKey("h3_cells.h3_index"), nullable=False),
        sa.Column("label", sa.String(50), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # ── outage_reports ────────────────────────────────────────────────────────
    op.create_table(
        "outage_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("lat", sa.Numeric(10, 7), nullable=True),
        sa.Column("lng", sa.Numeric(10, 7), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(20), server_default="app"),
        sa.Column("verified", sa.Boolean(), server_default="false"),
        sa.Column("verification_count", sa.Integer(), server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("idx_outage_h3", "outage_reports", ["h3_index"])
    op.create_index("idx_outage_time", "outage_reports", ["reported_at"])

    # ── predictions ───────────────────────────────────────────────────────────
    op.create_table(
        "predictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("model_version", sa.String(20), nullable=False),
        sa.Column("region_model", sa.String(50), nullable=False),
        sa.Column("features_snapshot", JSONB(), nullable=True),
    )
    op.create_index("idx_pred_h3_time", "predictions", ["h3_index", "predicted_at"])

    # ── weather_snapshots ─────────────────────────────────────────────────────
    op.create_table(
        "weather_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("temperature_c", sa.Numeric(5, 2), nullable=True),
        sa.Column("rainfall_mm", sa.Numeric(6, 2), nullable=True),
        sa.Column("wind_speed_ms", sa.Numeric(5, 2), nullable=True),
        sa.Column("humidity_pct", sa.Integer(), nullable=True),
        sa.Column("weather_code", sa.Integer(), nullable=True),
        sa.Column("is_forecast", sa.Boolean(), server_default="false"),
        sa.Column("forecast_source", sa.String(30), server_default="openweathermap"),
    )
    op.create_index("idx_weather_h3_time", "weather_snapshots", ["h3_index", "recorded_at"])

    # ── alert_subscriptions ───────────────────────────────────────────────────
    op.create_table(
        "alert_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("threshold_probability", sa.Numeric(4, 3), server_default="0.70"),
        sa.Column("channels", JSONB(), server_default='["sms","push"]'),
        sa.Column("quiet_hours_start", sa.Time(), nullable=True),
        sa.Column("quiet_hours_end", sa.Time(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
    )

    # ── push_subscriptions ────────────────────────────────────────────────────
    op.create_table(
        "push_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_push_user", "push_subscriptions", ["user_id"])

    # ── sms_alerts ────────────────────────────────────────────────────────────
    op.create_table(
        "sms_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("language", sa.String(5), server_default="en"),
        sa.Column("prediction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("provider", sa.String(30), nullable=True),
        sa.Column("smpp_message_id", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("idx_sms_user_time", "sms_alerts", ["user_id", "sent_at"])


def downgrade() -> None:
    op.drop_table("sms_alerts")
    op.drop_table("push_subscriptions")
    op.drop_table("alert_subscriptions")
    op.drop_table("weather_snapshots")
    op.drop_table("predictions")
    op.drop_table("outage_reports")
    op.drop_table("user_locations")
    op.drop_table("users")
    op.drop_table("h3_cells")
