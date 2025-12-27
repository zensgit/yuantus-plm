"""add cadgf artifact paths

Revision ID: h1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2025-01-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h1b2c3d4e5f6"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_document_path" not in columns:
        op.add_column("meta_files", sa.Column("cad_document_path", sa.String(), nullable=True))
    if "cad_manifest_path" not in columns:
        op.add_column("meta_files", sa.Column("cad_manifest_path", sa.String(), nullable=True))
    if "cad_metadata_path" not in columns:
        op.add_column("meta_files", sa.Column("cad_metadata_path", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_metadata_path" in columns:
        op.drop_column("meta_files", "cad_metadata_path")
    if "cad_manifest_path" in columns:
        op.drop_column("meta_files", "cad_manifest_path")
    if "cad_document_path" in columns:
        op.drop_column("meta_files", "cad_document_path")
