"""add job stale index

Revision ID: x1b2c3d4e7a2
Revises: w1b2c3d4e7a1
Create Date: 2026-02-12 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "x1b2c3d4e7a2"
down_revision: Union[str, None] = "w1b2c3d4e7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Supports stale job requeue queries:
    #   WHERE status='processing' AND started_at < cutoff
    op.create_index(
        "ix_meta_conversion_jobs_stale",
        "meta_conversion_jobs",
        ["status", "started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meta_conversion_jobs_stale",
        table_name="meta_conversion_jobs",
    )

