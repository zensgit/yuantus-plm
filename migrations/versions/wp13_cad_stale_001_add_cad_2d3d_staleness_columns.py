"""WP1.3: CAD 2D/3D staleness columns + meta_item_files (item_id,file_id,file_role) unique index

Revision ID: wp13_cad_stale_001
Revises: p2b_appr_tmpl_001
Create Date: 2026-06-05 00:00:00.000000

Adds the WP1.3 staleness/provenance columns to ``meta_item_files`` and
``meta_version_files`` (additive, nullable/defaulted, no backfill), and a unique
index ``uq_item_file_role`` on ``meta_item_files (item_id, file_id, file_role)``
to mirror ``VersionFile``'s existing ``(version_id, file_id, file_role)`` unique
index and keep WP1.3 model/drawing selection deterministic.

Before creating the unique index this migration DEDUPLICATES any pre-existing
duplicate ``(item_id, file_id, file_role)`` rows, keeping the earliest row by a
deterministic ``(created_at, id)`` ordering (NOT database natural order). In
practice there should be none -- both writers (``_attach_to_item`` and
``file_attachment_router``) historically kept <=1 row per ``(item_id, file_id)``
-- but the dedup makes ``alembic upgrade head`` robust on any historical state.

Idempotent: guards on existing columns/indexes so it is safe on a DB already
created via ``create_all`` (where the ORM models already declare these). Portable
across PostgreSQL and SQLite (dedup is done in Python; no PG-only SQL).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "wp13_cad_stale_001"
down_revision: Union[str, None] = "p2b_appr_tmpl_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ITEM_FILES = "meta_item_files"
_VERSION_FILES = "meta_version_files"

# (name, type, extra create_index?) for the 5 staleness columns.
_STALENESS_COLUMNS = (
    ("import_batch_id", sa.String(), True),
    ("source_batch_id", sa.String(), False),
    ("needs_update", sa.Boolean(), False),
    ("staleness_reason", sa.String(), False),
    ("staleness_checked_at", sa.DateTime(timezone=True), False),
)


def _existing_columns(insp, table: str) -> set[str]:
    return {c["name"] for c in insp.get_columns(table)}


def _existing_indexes(insp, table: str) -> set[str]:
    return {i["name"] for i in insp.get_indexes(table)}


def _add_staleness_columns(insp, table: str, with_batch_index: bool) -> None:
    cols = _existing_columns(insp, table)
    for name, coltype, want_index in _STALENESS_COLUMNS:
        if name in cols:
            continue
        if name == "needs_update":
            op.add_column(
                table,
                sa.Column(
                    "needs_update",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                ),
            )
        else:
            op.add_column(table, sa.Column(name, coltype, nullable=True))

    indexes = _existing_indexes(insp, table)
    # import_batch_id index (both tables); needs_update index (item_files only).
    batch_idx = f"ix_{table}_import_batch_id"
    if with_batch_index and batch_idx not in indexes:
        op.create_index(batch_idx, table, ["import_batch_id"], unique=False)
    if table == _ITEM_FILES:
        nu_idx = f"ix_{table}_needs_update"
        if nu_idx not in indexes:
            op.create_index(nu_idx, table, ["needs_update"], unique=False)


def _dedup_item_files(bind) -> None:
    """Delete duplicate (item_id, file_id, file_role) rows, deterministically
    keeping the earliest by (created_at, id). Python-side for PG/SQLite parity."""
    rows = bind.execute(
        sa.text(
            "SELECT id, item_id, file_id, file_role, created_at FROM meta_item_files"
        )
    ).fetchall()

    def _key(r):
        # None created_at sorts last; within groups compare created_at then id.
        return (r.created_at is None, r.created_at, str(r.id))

    seen: set = set()
    to_delete: list = []
    for r in sorted(rows, key=_key):
        k = (r.item_id, r.file_id, r.file_role)
        if k in seen:
            to_delete.append(r.id)
        else:
            seen.add(k)

    for dead_id in to_delete:
        bind.execute(
            sa.text("DELETE FROM meta_item_files WHERE id = :id"), {"id": dead_id}
        )


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if _ITEM_FILES in tables:
        _add_staleness_columns(insp, _ITEM_FILES, with_batch_index=True)
        # Re-inspect after column adds, then dedup + unique index.
        insp = sa.inspect(bind)
        if "uq_item_file_role" not in _existing_indexes(insp, _ITEM_FILES):
            _dedup_item_files(bind)
            op.create_index(
                "uq_item_file_role",
                _ITEM_FILES,
                ["item_id", "file_id", "file_role"],
                unique=True,
            )

    if _VERSION_FILES in tables:
        _add_staleness_columns(insp, _VERSION_FILES, with_batch_index=True)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if _ITEM_FILES in tables:
        indexes = _existing_indexes(insp, _ITEM_FILES)
        for idx in (
            "uq_item_file_role",
            f"ix_{_ITEM_FILES}_needs_update",
            f"ix_{_ITEM_FILES}_import_batch_id",
        ):
            if idx in indexes:
                op.drop_index(idx, table_name=_ITEM_FILES)
        cols = _existing_columns(insp, _ITEM_FILES)
        for name, _type, _idx in reversed(_STALENESS_COLUMNS):
            if name in cols:
                op.drop_column(_ITEM_FILES, name)

    if _VERSION_FILES in tables:
        indexes = _existing_indexes(insp, _VERSION_FILES)
        batch_idx = f"ix_{_VERSION_FILES}_import_batch_id"
        if batch_idx in indexes:
            op.drop_index(batch_idx, table_name=_VERSION_FILES)
        cols = _existing_columns(insp, _VERSION_FILES)
        for name, _type, _idx in reversed(_STALENESS_COLUMNS):
            if name in cols:
                op.drop_column(_VERSION_FILES, name)
