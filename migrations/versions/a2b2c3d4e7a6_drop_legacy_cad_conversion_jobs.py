"""drop legacy cad conversion jobs table

Revision ID: a2b2c3d4e7a6
Revises: z1b2c3d4e7a5
Create Date: 2026-04-14 13:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b2c3d4e7a6"
down_revision: Union[str, None] = "z1b2c3d4e7a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_LEGACY_TABLE = "cad_conversion_jobs"
_LEGACY_STATUS_INDEX = "ix_cad_conversion_jobs_status"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if _LEGACY_TABLE not in existing_tables:
        return

    existing_indexes = {
        idx.get("name")
        for idx in inspector.get_indexes(_LEGACY_TABLE)
        if idx.get("name")
    }
    if _LEGACY_STATUS_INDEX in existing_indexes:
        op.drop_index(_LEGACY_STATUS_INDEX, table_name=_LEGACY_TABLE)
    op.drop_table(_LEGACY_TABLE)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if _LEGACY_TABLE not in existing_tables:
        op.create_table(
            _LEGACY_TABLE,
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("source_file_id", sa.String(), nullable=False),
            sa.Column("target_format", sa.String(), nullable=False),
            sa.Column("operation_type", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("result_file_id", sa.String(), nullable=True),
            sa.Column("priority", sa.Integer(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=True),
            sa.Column("max_retries", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=True,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["result_file_id"], ["meta_files.id"]),
            sa.ForeignKeyConstraint(["source_file_id"], ["meta_files.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add(_LEGACY_TABLE)

    existing_indexes = {
        idx.get("name")
        for idx in inspector.get_indexes(_LEGACY_TABLE)
        if idx.get("name")
    }
    if _LEGACY_STATUS_INDEX not in existing_indexes:
        op.create_index(
            _LEGACY_STATUS_INDEX,
            _LEGACY_TABLE,
            ["status"],
            unique=False,
        )
