"""add file metadata columns

Revision ID: f1a2b3c4d5e6
Revises: g8f9a0b1c2d3
Create Date: 2025-12-22 21:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "g8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "author" not in columns:
        op.add_column("meta_files", sa.Column("author", sa.String(), nullable=True))
    if "source_system" not in columns:
        op.add_column(
            "meta_files", sa.Column("source_system", sa.String(), nullable=True)
        )
    if "source_version" not in columns:
        op.add_column(
            "meta_files", sa.Column("source_version", sa.String(), nullable=True)
        )
    if "document_version" not in columns:
        op.add_column(
            "meta_files", sa.Column("document_version", sa.String(), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "document_version" in columns:
        op.drop_column("meta_files", "document_version")
    if "source_version" in columns:
        op.drop_column("meta_files", "source_version")
    if "source_system" in columns:
        op.drop_column("meta_files", "source_system")
    if "author" in columns:
        op.drop_column("meta_files", "author")
