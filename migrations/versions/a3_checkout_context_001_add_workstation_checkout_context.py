"""Add workstation checkout context fields.

Revision ID: a3_checkout_context_001
Revises: b1_supersede_001
Create Date: 2026-06-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a3_checkout_context_001"
down_revision: Union[str, None] = "b1_supersede_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ("meta_item_versions", "meta_version_files")
_COLUMNS = (
    ("checkout_client_host", sa.String()),
    ("checkout_workspace_path", sa.String()),
    (
        "checkout_client_info",
        sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
    ),
)


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    for table in _TABLES:
        existing = _columns(table)
        for name, column_type in _COLUMNS:
            if name not in existing:
                op.add_column(table, sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    for table in reversed(_TABLES):
        existing = _columns(table)
        for name, _column_type in reversed(_COLUMNS):
            if name in existing:
                op.drop_column(table, name)
