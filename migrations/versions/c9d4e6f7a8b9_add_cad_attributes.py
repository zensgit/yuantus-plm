"""add cad attributes storage

Revision ID: c9d4e6f7a8b9
Revises: b7c9d2e1f4a6
Create Date: 2025-12-21 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c9d4e6f7a8b9"
down_revision: Union[str, None] = "b7c9d2e1f4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_attributes" not in columns:
        op.add_column(
            "meta_files",
            sa.Column(
                "cad_attributes",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
        )
    if "cad_attributes_source" not in columns:
        op.add_column(
            "meta_files",
            sa.Column("cad_attributes_source", sa.String(), nullable=True),
        )
    if "cad_attributes_updated_at" not in columns:
        op.add_column(
            "meta_files",
            sa.Column("cad_attributes_updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_attributes_updated_at" in columns:
        op.drop_column("meta_files", "cad_attributes_updated_at")
    if "cad_attributes_source" in columns:
        op.drop_column("meta_files", "cad_attributes_source")
    if "cad_attributes" in columns:
        op.drop_column("meta_files", "cad_attributes")
