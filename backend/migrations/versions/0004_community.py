"""community engagement — points, badges, notes, neighbor alerts

Revision ID: 0004
Revises: 0001
Create Date: 2026-05-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── user_points ───────────────────────────────────────────────────────────
    op.create_table(
        "user_points",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("total_points",   sa.Integer(), server_default="0"),
        sa.Column("weekly_points",  sa.Integer(), server_default="0"),
        sa.Column("monthly_points", sa.Integer(), server_default="0"),
        sa.Column("report_count",   sa.Integer(), server_default="0"),
        sa.Column("confirm_count",  sa.Integer(), server_default="0"),
        sa.Column("note_count",     sa.Integer(), server_default="0"),
        sa.Column("current_streak_days", sa.Integer(), server_default="0"),
        sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_points_user", "user_points", ["user_id"])
    op.create_index("idx_points_weekly", "user_points", ["weekly_points"])

    # ── user_badges ───────────────────────────────────────────────────────────
    op.create_table(
        "user_badges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("badge_key",         sa.String(50),  nullable=False),
        sa.Column("badge_name",        sa.String(100), nullable=False),
        sa.Column("badge_emoji",       sa.String(10),  nullable=False),
        sa.Column("badge_description", sa.String(200), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "badge_key", name="uq_user_badge"),
    )
    op.create_index("idx_badges_user", "user_badges", ["user_id"])

    # ── point_transactions ────────────────────────────────────────────────────
    op.create_table(
        "point_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("points",       sa.Integer(), nullable=False),
        sa.Column("action",       sa.String(50), nullable=False),
        sa.Column("reference_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tx_user", "point_transactions", ["user_id", "created_at"])

    # ── community_notes ───────────────────────────────────────────────────────
    op.create_table(
        "community_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",  UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("body",     sa.String(280), nullable=False),
        sa.Column("upvotes",  sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_notes_h3_active", "community_notes", ["h3_index", "is_active"])

    # ── note_upvotes ──────────────────────────────────────────────────────────
    op.create_table(
        "note_upvotes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("note_id", UUID(as_uuid=True), sa.ForeignKey("community_notes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("note_id", "user_id", name="uq_note_upvote"),
    )

    # ── neighbor_alert_log ────────────────────────────────────────────────────
    op.create_table(
        "neighbor_alert_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("triggered_by_report_id", sa.String(50), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("recipients_count", sa.Integer(), server_default="0"),
    )
    op.create_index("idx_neighbor_log_h3", "neighbor_alert_log", ["h3_index", "sent_at"])


def downgrade() -> None:
    op.drop_table("neighbor_alert_log")
    op.drop_table("note_upvotes")
    op.drop_table("community_notes")
    op.drop_table("point_transactions")
    op.drop_table("user_badges")
    op.drop_table("user_points")
