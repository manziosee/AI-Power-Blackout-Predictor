"""0041 notification preferences and feed

Revision ID: 0041
Revises: 0040
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    try:
        return "postgresql" in str(op.get_bind().engine.url)
    except Exception:
        return False


def upgrade() -> None:
    pg = _is_pg()
    uuid_type = postgresql.UUID(as_uuid=True) if pg else sa.String(36)
    jsonb_type = postgresql.JSONB() if pg else sa.Text()

    op.create_table(
        "user_notification_preferences",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("channels", jsonb_type, nullable=False, server_default='["sms","push"]'),
        sa.Column("default_threshold", sa.Float(), nullable=False, server_default="0.70"),
        sa.Column("quiet_hours_start", sa.Time(), nullable=True),
        sa.Column("quiet_hours_end", sa.Time(), nullable=True),
        sa.Column("quiet_risk_override", sa.String(20), nullable=True),
        sa.Column("all_notifications_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_user_notif_prefs_user_id", "user_notification_preferences", ["user_id"])

    op.create_table(
        "notification_feed",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("h3_index", sa.String(15), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notification_feed_user_id", "notification_feed", ["user_id"])
    op.create_index("ix_notification_feed_created_at", "notification_feed", ["created_at"])
    op.create_index("ix_notification_feed_h3_index", "notification_feed", ["h3_index"])


def downgrade() -> None:
    op.drop_index("ix_notification_feed_h3_index", table_name="notification_feed")
    op.drop_index("ix_notification_feed_created_at", table_name="notification_feed")
    op.drop_index("ix_notification_feed_user_id", table_name="notification_feed")
    op.drop_table("notification_feed")
    op.drop_index("ix_user_notif_prefs_user_id", table_name="user_notification_preferences")
    op.drop_table("user_notification_preferences")
