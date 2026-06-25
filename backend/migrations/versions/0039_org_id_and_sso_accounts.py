"""0039 add org_id to users and create sso_accounts table

Revision ID: 0039
Revises: 0038
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def _is_pg() -> bool:
    try:
        return "postgresql" in str(op.get_bind().engine.url)
    except Exception:
        return False


def upgrade() -> None:
    if _is_pg():
        op.add_column(
            "users",
            sa.Column(
                "org_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("organizations.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_table(
            "sso_accounts",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("provider", sa.String(30), nullable=False),
            sa.Column("provider_user_id", sa.String(200), nullable=False),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    else:
        op.add_column("users", sa.Column("org_id", sa.String(36), nullable=True))
        op.create_table(
            "sso_accounts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("provider", sa.String(30), nullable=False),
            sa.Column("provider_user_id", sa.String(200), nullable=False),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_sso_accounts_user_id", "sso_accounts", ["user_id"])
    op.create_unique_constraint(
        "uq_sso_provider_uid", "sso_accounts", ["provider", "provider_user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_sso_provider_uid", "sso_accounts", type_="unique")
    op.drop_index("ix_sso_accounts_user_id", table_name="sso_accounts")
    op.drop_table("sso_accounts")
    op.drop_index("ix_users_org_id", table_name="users")
    op.drop_column("users", "org_id")
