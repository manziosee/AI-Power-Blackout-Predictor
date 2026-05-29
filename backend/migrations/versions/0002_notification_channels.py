"""notification channels — whatsapp, telegram, email subscriptions

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── whatsapp_subscriptions ────────────────────────────────────────────────
    op.create_table(
        "whatsapp_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("opted_in_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_wa_user", "whatsapp_subscriptions", ["user_id"])

    # ── telegram_subscriptions ────────────────────────────────────────────────
    op.create_table(
        "telegram_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("chat_id", sa.String(30), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("h3_index", sa.String(15), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_tg_user", "telegram_subscriptions", ["user_id"])
    op.create_index("idx_tg_h3", "telegram_subscriptions", ["h3_index"])

    # ── email_subscriptions ───────────────────────────────────────────────────
    op.create_table(
        "email_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("subscribed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("last_digest_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_email_user", "email_subscriptions", ["user_id"])


def downgrade() -> None:
    op.drop_table("email_subscriptions")
    op.drop_table("telegram_subscriptions")
    op.drop_table("whatsapp_subscriptions")
