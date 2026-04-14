"""merge alembic heads and add eco routing changes table

Revision ID: c1d2e3f4a5b6
Revises: a2b2c3d4e7a6, f7a8b9c0d1e2
Create Date: 2026-04-15 09:40:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = ("a2b2c3d4e7a6", "f7a8b9c0d1e2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _j() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {ix.get("name") for ix in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_eco_routing_changes" not in existing:
        op.create_table(
            "meta_eco_routing_changes",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("eco_id", sa.String(), nullable=False),
            sa.Column("routing_id", sa.String(), nullable=True),
            sa.Column("operation_id", sa.String(), nullable=True),
            sa.Column("change_type", sa.String(length=10), nullable=False),
            sa.Column("old_snapshot", _j(), nullable=True),
            sa.Column("new_snapshot", _j(), nullable=True),
            sa.Column("conflict", sa.Boolean(), nullable=True),
            sa.Column("conflict_reason", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["eco_id"], ["meta_ecos.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing.add("meta_eco_routing_changes")

    _ensure_index(
        "meta_eco_routing_changes",
        op.f("ix_meta_eco_routing_changes_eco_id"),
        ["eco_id"],
    )
    _ensure_index(
        "meta_eco_routing_changes",
        op.f("ix_meta_eco_routing_changes_change_type"),
        ["change_type"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_eco_routing_changes" not in existing:
        return

    existing_indexes = {ix.get("name") for ix in inspector.get_indexes("meta_eco_routing_changes")}
    for index_name in (
        op.f("ix_meta_eco_routing_changes_change_type"),
        op.f("ix_meta_eco_routing_changes_eco_id"),
    ):
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="meta_eco_routing_changes")
    op.drop_table("meta_eco_routing_changes")
