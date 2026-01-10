"""add cad document schema version and properties

Revision ID: i1b2c3d4e5f7
Revises: h1b2c3d4e5f6
Create Date: 2026-01-09 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "i1b2c3d4e5f7"
down_revision: Union[str, None] = "h1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_document_schema_version" not in columns:
        op.add_column(
            "meta_files",
            sa.Column("cad_document_schema_version", sa.Integer(), nullable=True),
        )
    if "cad_properties" not in columns:
        op.add_column(
            "meta_files",
            sa.Column(
                "cad_properties",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
        )
    if "cad_properties_source" not in columns:
        op.add_column(
            "meta_files",
            sa.Column("cad_properties_source", sa.String(), nullable=True),
        )
    if "cad_properties_updated_at" not in columns:
        op.add_column(
            "meta_files",
            sa.Column("cad_properties_updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_properties_updated_at" in columns:
        op.drop_column("meta_files", "cad_properties_updated_at")
    if "cad_properties_source" in columns:
        op.drop_column("meta_files", "cad_properties_source")
    if "cad_properties" in columns:
        op.drop_column("meta_files", "cad_properties")
    if "cad_document_schema_version" in columns:
        op.drop_column("meta_files", "cad_document_schema_version")
