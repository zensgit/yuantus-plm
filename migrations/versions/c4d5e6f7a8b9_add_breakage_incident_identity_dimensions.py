"""add breakage incident identity and dimensions

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-04 16:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_breakage_incidents" not in inspector.get_table_names():
        return

    columns = {
        column["name"] for column in inspector.get_columns("meta_breakage_incidents")
    }

    if "incident_code" not in columns:
        op.add_column(
            "meta_breakage_incidents",
            sa.Column("incident_code", sa.String(length=40), nullable=True),
        )
    if "bom_id" not in columns:
        op.add_column(
            "meta_breakage_incidents",
            sa.Column("bom_id", sa.String(), nullable=True),
        )
    if "mbom_id" not in columns:
        op.add_column(
            "meta_breakage_incidents",
            sa.Column("mbom_id", sa.String(), nullable=True),
        )
    if "routing_id" not in columns:
        op.add_column(
            "meta_breakage_incidents",
            sa.Column("routing_id", sa.String(length=120), nullable=True),
        )

    index_names = _index_names(inspector, "meta_breakage_incidents")
    if "ix_meta_breakage_incidents_incident_code" not in index_names:
        op.create_index(
            op.f("ix_meta_breakage_incidents_incident_code"),
            "meta_breakage_incidents",
            ["incident_code"],
            unique=True,
        )
    if "ix_meta_breakage_incidents_bom_id" not in index_names:
        op.create_index(
            op.f("ix_meta_breakage_incidents_bom_id"),
            "meta_breakage_incidents",
            ["bom_id"],
            unique=False,
        )
    if "ix_meta_breakage_incidents_mbom_id" not in index_names:
        op.create_index(
            op.f("ix_meta_breakage_incidents_mbom_id"),
            "meta_breakage_incidents",
            ["mbom_id"],
            unique=False,
        )
    if "ix_meta_breakage_incidents_routing_id" not in index_names:
        op.create_index(
            op.f("ix_meta_breakage_incidents_routing_id"),
            "meta_breakage_incidents",
            ["routing_id"],
            unique=False,
        )

    rows = list(
        bind.execute(
            sa.text(
                """
                SELECT id, incident_code, version_id, production_order_id, mbom_id, routing_id
                FROM meta_breakage_incidents
                ORDER BY created_at ASC, id ASC
                """
            )
        )
    )

    max_sequence = 0
    for row in rows:
        code = str(row.incident_code or "").strip().upper()
        if code.startswith("BRK-") and code[4:].isdigit():
            max_sequence = max(max_sequence, int(code[4:]))

    for row in rows:
        updates: dict[str, object] = {}
        if not str(row.mbom_id or "").strip() and str(row.version_id or "").strip():
            updates["mbom_id"] = str(row.version_id).strip()
        if not str(row.routing_id or "").strip() and str(row.production_order_id or "").strip():
            updates["routing_id"] = str(row.production_order_id).strip()
        if not str(row.incident_code or "").strip():
            max_sequence += 1
            updates["incident_code"] = f"BRK-{max_sequence:06d}"
        if not updates:
            continue
        assignments = ", ".join(f"{column} = :{column}" for column in updates)
        bind.execute(
            sa.text(
                f"UPDATE meta_breakage_incidents SET {assignments} WHERE id = :incident_id"
            ),
            {"incident_id": row.id, **updates},
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_breakage_incidents" not in inspector.get_table_names():
        return

    columns = {
        column["name"] for column in inspector.get_columns("meta_breakage_incidents")
    }
    index_names = _index_names(inspector, "meta_breakage_incidents")

    if "ix_meta_breakage_incidents_routing_id" in index_names:
        op.drop_index(
            op.f("ix_meta_breakage_incidents_routing_id"),
            table_name="meta_breakage_incidents",
        )
    if "ix_meta_breakage_incidents_mbom_id" in index_names:
        op.drop_index(
            op.f("ix_meta_breakage_incidents_mbom_id"),
            table_name="meta_breakage_incidents",
        )
    if "ix_meta_breakage_incidents_bom_id" in index_names:
        op.drop_index(
            op.f("ix_meta_breakage_incidents_bom_id"),
            table_name="meta_breakage_incidents",
        )
    if "ix_meta_breakage_incidents_incident_code" in index_names:
        op.drop_index(
            op.f("ix_meta_breakage_incidents_incident_code"),
            table_name="meta_breakage_incidents",
        )

    if "routing_id" in columns:
        op.drop_column("meta_breakage_incidents", "routing_id")
    if "mbom_id" in columns:
        op.drop_column("meta_breakage_incidents", "mbom_id")
    if "bom_id" in columns:
        op.drop_column("meta_breakage_incidents", "bom_id")
    if "incident_code" in columns:
        op.drop_column("meta_breakage_incidents", "incident_code")
