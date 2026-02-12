"""add app store tables

Revision ID: w1b2c3d4e7a1
Revises: v1b2c3d4e7a0
Create Date: 2026-02-12 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "w1b2c3d4e7a1"
down_revision: Union[str, None] = "v1b2c3d4e7a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meta_store_listings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("latest_version", sa.String(length=50), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("price_model", sa.String(length=50), nullable=True),
        sa.Column("price_amount", sa.Integer(), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("publisher", sa.String(length=100), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_meta_store_listings_name"),
        "meta_store_listings",
        ["name"],
        unique=False,
    )

    op.create_table(
        "meta_app_licenses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("app_registry_id", sa.String(), nullable=True),
        sa.Column("app_name", sa.String(length=100), nullable=False),
        sa.Column("license_key", sa.String(length=100), nullable=False),
        sa.Column("plan_type", sa.String(length=50), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column(
            "license_data",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["app_registry_id"],
            ["meta_app_registry.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("license_key"),
    )


def downgrade() -> None:
    op.drop_table("meta_app_licenses")
    op.drop_index(op.f("ix_meta_store_listings_name"), table_name="meta_store_listings")
    op.drop_table("meta_store_listings")

