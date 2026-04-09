"""add document sync site auth contract

Revision ID: e6f7a8b9c0d1
Revises: c4d5e6f7a8b9
Create Date: 2026-04-07 00:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _j() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_sync_sites" not in inspector.get_table_names():
        return

    columns = {
        column["name"] for column in inspector.get_columns("meta_sync_sites")
    }

    if "auth_type" not in columns:
        op.add_column(
            "meta_sync_sites",
            sa.Column("auth_type", sa.String(length=30), nullable=True),
        )
    if "auth_config" not in columns:
        op.add_column(
            "meta_sync_sites",
            sa.Column("auth_config", _j(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_sync_sites" not in inspector.get_table_names():
        return

    columns = {
        column["name"] for column in inspector.get_columns("meta_sync_sites")
    }

    if "auth_config" in columns:
        op.drop_column("meta_sync_sites", "auth_config")
    if "auth_type" in columns:
        op.drop_column("meta_sync_sites", "auth_type")
