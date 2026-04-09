"""add subcontract approval role mappings

Revision ID: b3c4d5e6f7a8
Revises: z1b2c3d4e7a5
Create Date: 2026-03-23 22:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "z1b2c3d4e7a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _j() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_subcontract_approval_role_mappings" not in existing:
        op.create_table(
            "meta_subcontract_approval_role_mappings",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("role_code", sa.String(length=100), nullable=False),
            sa.Column("scope_type", sa.String(length=30), nullable=False),
            sa.Column("scope_value", sa.String(length=200), nullable=True),
            sa.Column("owner", sa.String(length=200), nullable=True),
            sa.Column("team", sa.String(length=200), nullable=True),
            sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default=sa.text("10")),
            sa.Column("fallback_role", sa.String(length=100), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("properties", _j(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_subcontract_approval_role_mappings_role_code"),
            "meta_subcontract_approval_role_mappings",
            ["role_code"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_subcontract_approval_role_mappings_scope_type"),
            "meta_subcontract_approval_role_mappings",
            ["scope_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_subcontract_approval_role_mappings_scope_value"),
            "meta_subcontract_approval_role_mappings",
            ["scope_value"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_subcontract_approval_role_mappings" in existing:
        op.drop_index(
            op.f("ix_meta_subcontract_approval_role_mappings_scope_value"),
            table_name="meta_subcontract_approval_role_mappings",
        )
        op.drop_index(
            op.f("ix_meta_subcontract_approval_role_mappings_scope_type"),
            table_name="meta_subcontract_approval_role_mappings",
        )
        op.drop_index(
            op.f("ix_meta_subcontract_approval_role_mappings_role_code"),
            table_name="meta_subcontract_approval_role_mappings",
        )
        op.drop_table("meta_subcontract_approval_role_mappings")
