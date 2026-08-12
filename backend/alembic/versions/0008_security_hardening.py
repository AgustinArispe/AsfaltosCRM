"""Add durable User authentication session versions.

Revision ID: 0008_security_hardening
Revises: 0007_crm_commercial_completion
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_security_hardening"
down_revision: str | Sequence[str] | None = "0007_crm_commercial_completion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "auth_session_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_users_auth_session_version_positive",
        "users",
        "auth_session_version > 0",
    )
    op.alter_column("users", "auth_session_version", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_users_auth_session_version_positive",
        "users",
        type_="check",
    )
    op.drop_column("users", "auth_session_version")
