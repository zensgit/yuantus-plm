"""add plugin configs

Revision ID: m1b2c3d4e6a1
Revises: l1b2c3d4e6a0
Create Date: 2026-01-11 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "m1b2c3d4e6a1"
down_revision: Union[str, None] = "l1b2c3d4e6a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_plugin_configs" in inspector.get_table_names():
        return

    op.create_table(
        "meta_plugin_configs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("plugin_id", sa.String(length=120), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=120), nullable=False, index=True),
        sa.Column("org_id", sa.String(length=120), nullable=False, index=True),
        sa.Column(
            "config",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "plugin_id", "tenant_id", "org_id", name="uq_plugin_config_scope"
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_plugin_configs" not in inspector.get_table_names():
        return

    op.drop_table("meta_plugin_configs")
