"""0023 push subscriptions add is_active updated_at

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("push_subscriptions") as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("push_subscriptions") as batch_op:
        batch_op.drop_column("is_active")
        batch_op.drop_column("updated_at")
