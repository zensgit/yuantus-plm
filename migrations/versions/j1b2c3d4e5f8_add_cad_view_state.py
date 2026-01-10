"""add cad view state

Revision ID: j1b2c3d4e5f8
Revises: i1b2c3d4e5f7
Create Date: 2026-01-09 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "j1b2c3d4e5f8"
down_revision: Union[str, None] = "i1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_view_state" not in columns:
        op.add_column(
            "meta_files",
            sa.Column(
                "cad_view_state",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
        )
    if "cad_view_state_source" not in columns:
        op.add_column(
            "meta_files",
            sa.Column("cad_view_state_source", sa.String(), nullable=True),
        )
    if "cad_view_state_updated_at" not in columns:
        op.add_column(
            "meta_files",
            sa.Column("cad_view_state_updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_view_state_updated_at" in columns:
        op.drop_column("meta_files", "cad_view_state_updated_at")
    if "cad_view_state_source" in columns:
        op.drop_column("meta_files", "cad_view_state_source")
    if "cad_view_state" in columns:
        op.drop_column("meta_files", "cad_view_state")
