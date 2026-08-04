"""Initial database schema baseline.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-04
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Establish the migration baseline before CRM models are introduced."""


def downgrade() -> None:
    """No schema objects exist in the baseline migration."""
