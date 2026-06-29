"""add meta_bom_writeback_audit (Phase 7 governed BOM multi-table write-back)

One row per governed BOM multi-table line write-back: the UNIQUE ``idempotency_key`` is BOTH the
single-use/replay guard AND the before/after audit diff (#901 §2/§3), committed atomically with
the in-place property mutation. ``user_id`` is intentionally FK-free (audit immutability +
system/automated writes with an unvalidated user id), mirroring the transition-history precedent.

Revision ID: p7_bom_writeback_001
Revises: txn_history_001
Create Date: 2026-06-29 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p7_bom_writeback_001"
down_revision: Union[str, None] = "txn_history_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "meta_bom_writeback_audit"


def upgrade() -> None:
    bind = op.get_bind()
    if _TABLE in set(sa.inspect(bind).get_table_names()):
        return
    op.create_table(
        "meta_bom_writeback_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.Column("part_id", sa.String(), nullable=False),
        sa.Column("bom_line_id", sa.String(), nullable=False),
        sa.Column(
            "before", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
        ),
        sa.Column(
            "after", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
        ),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'applied'")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # idempotency_key carries the single-use guarantee -> a UNIQUE index (matches the model's
    # Column(unique=True, index=True)); the rest are plain lookup indexes.
    op.create_index(
        op.f("ix_meta_bom_writeback_audit_idempotency_key"),
        _TABLE,
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(op.f("ix_meta_bom_writeback_audit_part_id"), _TABLE, ["part_id"], unique=False)
    op.create_index(
        op.f("ix_meta_bom_writeback_audit_bom_line_id"), _TABLE, ["bom_line_id"], unique=False
    )
    op.create_index(
        op.f("ix_meta_bom_writeback_audit_tenant_id"), _TABLE, ["tenant_id"], unique=False
    )
    op.create_index(op.f("ix_meta_bom_writeback_audit_org_id"), _TABLE, ["org_id"], unique=False)
    op.create_index(op.f("ix_meta_bom_writeback_audit_user_id"), _TABLE, ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_meta_bom_writeback_audit_user_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_meta_bom_writeback_audit_org_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_meta_bom_writeback_audit_tenant_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_meta_bom_writeback_audit_bom_line_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_meta_bom_writeback_audit_part_id"), table_name=_TABLE)
    op.drop_index(op.f("ix_meta_bom_writeback_audit_idempotency_key"), table_name=_TABLE)
    op.drop_table(_TABLE)
