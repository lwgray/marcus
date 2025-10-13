"""Add user_roles table and update users table with is_active, is_verified, last_login.

Revision ID: add_user_roles_fields
Revises: 8f03f242faea
Create Date: 2025-10-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_user_roles_fields"
down_revision: Union[str, None] = "8f03f242faea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema by adding user_roles table and new user fields."""
    # Add new columns to users table
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users", sa.Column("last_login", sa.DateTime(timezone=True), nullable=True)
    )

    # Create user_roles table
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("granted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", name="uq_user_role"),
    )
    op.create_index("ix_user_roles_role", "user_roles", ["role"], unique=False)
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"], unique=False)
    op.create_index(
        "ix_user_roles_user_id_role", "user_roles", ["user_id", "role"], unique=False
    )


def downgrade() -> None:
    """Downgrade database schema by removing user_roles table and new user fields."""
    # Drop user_roles table and indexes
    op.drop_index("ix_user_roles_user_id_role", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_index("ix_user_roles_role", table_name="user_roles")
    op.drop_table("user_roles")

    # Remove columns from users table
    op.drop_column("users", "last_login")
    op.drop_column("users", "is_verified")
    op.drop_column("users", "is_active")
