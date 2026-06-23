"""0034 add retry fields and template fields to sms_alerts

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    try:
        return "postgresql" in str(op.get_bind().engine.url)
    except Exception:
        return False


def upgrade() -> None:
    with op.batch_alter_table("sms_alerts") as batch_op:
        batch_op.add_column(sa.Column("template_key", sa.String(50), nullable=True))
        if _is_pg():
            batch_op.add_column(sa.Column("template_vars", postgresql.JSONB(), nullable=True))
        else:
            batch_op.add_column(sa.Column("template_vars", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sms_alerts") as batch_op:
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("retry_count")
        batch_op.drop_column("template_vars")
        batch_op.drop_column("template_key")
