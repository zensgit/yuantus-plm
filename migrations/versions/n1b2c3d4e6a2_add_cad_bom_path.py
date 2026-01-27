"""add cad_bom_path to meta_files

Revision ID: n1b2c3d4e6a2
Revises: m1b2c3d4e6a1
Create Date: 2026-01-27 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "n1b2c3d4e6a2"
down_revision: Union[str, None] = "m1b2c3d4e6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_bom_path" not in columns:
        op.add_column("meta_files", sa.Column("cad_bom_path", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_bom_path" in columns:
        op.drop_column("meta_files", "cad_bom_path")
