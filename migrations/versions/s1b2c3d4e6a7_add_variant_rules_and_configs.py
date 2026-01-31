"""add variant rules and product configurations

Revision ID: s1b2c3d4e6a7
Revises: r1b2c3d4e6a6
Create Date: 2026-01-31 13:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "s1b2c3d4e6a7"
down_revision: Union[str, None] = "r1b2c3d4e6a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if "meta_config_option_sets" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("meta_config_option_sets")}
        if "value_type" not in columns:
            op.add_column(
                "meta_config_option_sets",
                sa.Column("value_type", sa.String(length=50), nullable=True, server_default="string"),
            )
        if "allow_multiple" not in columns:
            op.add_column(
                "meta_config_option_sets",
                sa.Column("allow_multiple", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
        if "is_required" not in columns:
            op.add_column(
                "meta_config_option_sets",
                sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            )
        if "default_value" not in columns:
            op.add_column(
                "meta_config_option_sets",
                sa.Column("default_value", sa.String(length=200), nullable=True),
            )
        if "sequence" not in columns:
            op.add_column(
                "meta_config_option_sets",
                sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
            )
        if "created_by_id" not in columns:
            op.add_column(
                "meta_config_option_sets",
                sa.Column("created_by_id", sa.Integer(), nullable=True),
            )

    if "meta_config_options" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("meta_config_options")}
        if "description" not in columns:
            op.add_column(
                "meta_config_options",
                sa.Column("description", sa.Text(), nullable=True),
            )
        if "ref_item_id" not in columns:
            op.add_column(
                "meta_config_options",
                sa.Column("ref_item_id", sa.String(length=36), nullable=True),
            )
        if "is_active" not in columns:
            op.add_column(
                "meta_config_options",
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            )

    if "meta_variant_rules" not in existing_tables:
        op.create_table(
            "meta_variant_rules",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("parent_item_type_id", sa.String(length=120), nullable=True, index=True),
            sa.Column("parent_item_id", sa.String(length=36), nullable=True, index=True),
            sa.Column(
                "condition",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=False,
            ),
            sa.Column("action_type", sa.String(length=50), nullable=False),
            sa.Column("target_item_id", sa.String(length=36), nullable=True),
            sa.Column("target_relationship_id", sa.String(length=36), nullable=True),
            sa.Column(
                "action_params",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["parent_item_type_id"], ["meta_item_types.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["parent_item_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["target_item_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["target_relationship_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_product_configurations" not in existing_tables:
        op.create_table(
            "meta_product_configurations",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("product_item_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "selections",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=False,
            ),
            sa.Column(
                "effective_bom_cache",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("cache_updated_at", sa.DateTime(), nullable=True),
            sa.Column("state", sa.String(length=50), nullable=False, server_default="draft"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("released_at", sa.DateTime(), nullable=True),
            sa.Column("released_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["product_item_id"], ["meta_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["released_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_tables = set(inspector.get_table_names())

    if "meta_product_configurations" in existing_tables:
        op.drop_table("meta_product_configurations")
    if "meta_variant_rules" in existing_tables:
        op.drop_table("meta_variant_rules")

    if "meta_config_options" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("meta_config_options")}
        if "is_active" in columns:
            op.drop_column("meta_config_options", "is_active")
        if "ref_item_id" in columns:
            op.drop_column("meta_config_options", "ref_item_id")
        if "description" in columns:
            op.drop_column("meta_config_options", "description")

    if "meta_config_option_sets" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("meta_config_option_sets")}
        if "created_by_id" in columns:
            op.drop_column("meta_config_option_sets", "created_by_id")
        if "sequence" in columns:
            op.drop_column("meta_config_option_sets", "sequence")
        if "default_value" in columns:
            op.drop_column("meta_config_option_sets", "default_value")
        if "is_required" in columns:
            op.drop_column("meta_config_option_sets", "is_required")
        if "allow_multiple" in columns:
            op.drop_column("meta_config_option_sets", "allow_multiple")
        if "value_type" in columns:
            op.drop_column("meta_config_option_sets", "value_type")
