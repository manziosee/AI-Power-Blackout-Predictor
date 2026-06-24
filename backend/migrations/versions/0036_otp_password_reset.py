"""0036 add OTP fields to users for SMS password reset

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("otp_code_hash", sa.String(64), nullable=True))
        batch_op.add_column(
            sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("otp_expires_at")
        batch_op.drop_column("otp_code_hash")
