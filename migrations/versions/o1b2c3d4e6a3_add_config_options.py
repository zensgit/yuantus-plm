"""add config option sets

Revision ID: o1b2c3d4e6a3
Revises: n1b2c3d4e6a2
Create Date: 2026-01-28 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "o1b2c3d4e6a3"
down_revision: Union[str, None] = "n1b2c3d4e6a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing = set(inspector.get_table_names())

    if "meta_config_option_sets" not in existing:
        op.create_table(
            "meta_config_option_sets",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("name", sa.String(length=120), nullable=False, index=True),
            sa.Column("label", sa.String(length=200), nullable=True),
            sa.Column("description", sa.String(), nullable=True),
            sa.Column("item_type_id", sa.String(length=120), nullable=True, index=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "config",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("name", name="uq_config_option_set_name"),
        )

    if "meta_config_options" not in existing:
        op.create_table(
            "meta_config_options",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("option_set_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("key", sa.String(length=120), nullable=False),
            sa.Column("label", sa.String(length=200), nullable=True),
            sa.Column("value", sa.String(length=200), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column(
                "extra",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["option_set_id"],
                ["meta_config_option_sets.id"],
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "option_set_id", "key", name="uq_config_option_key"
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing = set(inspector.get_table_names())

    if "meta_config_options" in existing:
        op.drop_table("meta_config_options")
    if "meta_config_option_sets" in existing:
        op.drop_table("meta_config_option_sets")
