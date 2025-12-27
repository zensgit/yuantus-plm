"""add_tenant_quotas

Revision ID: g8f9a0b1c2d3
Revises: d4f1a2b3c4d5
Create Date: 2025-01-10 00:00:00.000000
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "g8f9a0b1c2d3"
down_revision: Union[str, None] = "d4f1a2b3c4d5"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "auth_tenant_quotas",
        sa.Column("tenant_id", sa.String(length=64), primary_key=True),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("max_orgs", sa.Integer(), nullable=True),
        sa.Column("max_files", sa.Integer(), nullable=True),
        sa.Column("max_storage_bytes", sa.BigInteger(), nullable=True),
        sa.Column("max_active_jobs", sa.Integer(), nullable=True),
        sa.Column("max_processing_jobs", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["auth_tenants.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("auth_tenant_quotas")
