"""add project management settings

Revision ID: 003
Revises: 002
Create Date: 2026-07-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("projects", sa.Column("timeout_seconds", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("retention_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "retention_days")
    op.drop_column("projects", "timeout_seconds")
    op.drop_column("projects", "enabled")
