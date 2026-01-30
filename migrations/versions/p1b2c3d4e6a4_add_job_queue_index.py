"""add job queue index

Revision ID: p1b2c3d4e6a4
Revises: o1b2c3d4e6a3
Create Date: 2026-01-30 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "p1b2c3d4e6a4"
down_revision: Union[str, None] = "o1b2c3d4e6a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_meta_conversion_jobs_queue",
        "meta_conversion_jobs",
        ["status", "scheduled_at", "priority", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_meta_conversion_jobs_queue",
        table_name="meta_conversion_jobs",
    )
