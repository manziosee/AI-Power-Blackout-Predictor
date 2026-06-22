"""0031 add location_type and display_order to user_locations

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_locations") as batch_op:
        batch_op.add_column(
            sa.Column("location_type", sa.String(20), nullable=True)
        )
        batch_op.add_column(
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("user_locations") as batch_op:
        batch_op.drop_column("display_order")
        batch_op.drop_column("location_type")
