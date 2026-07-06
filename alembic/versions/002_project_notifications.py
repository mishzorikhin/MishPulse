"""add per-project ntfy and telegram notification settings

Revision ID: 002
Revises: 001
Create Date: 2026-07-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("ntfy_server", sa.String(length=500), nullable=True))
    op.add_column("projects", sa.Column("ntfy_topic", sa.String(length=200), nullable=True))
    op.add_column(
        "projects", sa.Column("telegram_bot_token", sa.String(length=200), nullable=True)
    )
    op.add_column("projects", sa.Column("telegram_chat_id", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "telegram_chat_id")
    op.drop_column("projects", "telegram_bot_token")
    op.drop_column("projects", "ntfy_topic")
    op.drop_column("projects", "ntfy_server")
