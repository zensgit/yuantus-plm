"""add cad_dedup_path to meta_files

Revision ID: q1b2c3d4e6a5
Revises: p1b2c3d4e6a4
Create Date: 2026-01-30 12:20:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "q1b2c3d4e6a5"
down_revision: Union[str, None] = "p1b2c3d4e6a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_dedup_path" not in columns:
        op.add_column("meta_files", sa.Column("cad_dedup_path", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_dedup_path" in columns:
        op.drop_column("meta_files", "cad_dedup_path")
