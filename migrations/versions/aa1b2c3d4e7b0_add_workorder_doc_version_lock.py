"""add workorder document version-lock columns

Revision ID: aa1b2c3d4e7b0
Revises: f4a5b6c7d8e9
Create Date: 2026-05-15 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aa1b2c3d4e7b0"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "meta_workorder_document_links"
_NEW_COLUMNS = ("document_version_id", "version_locked_at", "version_lock_source")
_NEW_INDEX = "ix_meta_workorder_document_links_document_version_id"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in set(inspector.get_table_names()):
        return

    existing_columns = {col["name"] for col in inspector.get_columns(_TABLE)}

    if "document_version_id" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("document_version_id", sa.String(), nullable=True),
        )
    if "version_locked_at" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("version_locked_at", sa.DateTime(), nullable=True),
        )
    if "version_lock_source" not in existing_columns:
        op.add_column(
            _TABLE,
            sa.Column("version_lock_source", sa.String(length=40), nullable=True),
        )

    existing_indexes = {ix["name"] for ix in inspector.get_indexes(_TABLE)}
    if _NEW_INDEX not in existing_indexes:
        op.create_index(
            op.f(_NEW_INDEX),
            _TABLE,
            ["document_version_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE not in set(inspector.get_table_names()):
        return

    existing_indexes = {ix["name"] for ix in inspector.get_indexes(_TABLE)}
    if _NEW_INDEX in existing_indexes:
        op.drop_index(op.f(_NEW_INDEX), table_name=_TABLE)

    existing_columns = {col["name"] for col in inspector.get_columns(_TABLE)}
    for column in _NEW_COLUMNS:
        if column in existing_columns:
            op.drop_column(_TABLE, column)
