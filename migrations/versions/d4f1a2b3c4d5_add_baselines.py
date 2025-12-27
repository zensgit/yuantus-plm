"""add baselines

Revision ID: d4f1a2b3c4d5
Revises: c9d4e6f7a8b9
Create Date: 2025-12-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d4f1a2b3c4d5"
down_revision: Union[str, None] = "c9d4e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_baselines" not in inspector.get_table_names():
        op.create_table(
            "meta_baselines",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("baseline_type", sa.String(length=50), nullable=False, server_default="bom"),
            sa.Column("root_item_id", sa.String(), nullable=True),
            sa.Column("root_version_id", sa.String(), nullable=True),
            sa.Column("root_config_id", sa.String(), nullable=True),
            sa.Column(
                "snapshot",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=False,
            ),
            sa.Column("max_levels", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("effective_at", sa.DateTime(), nullable=True),
            sa.Column("include_substitutes", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("include_effectivity", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("line_key", sa.String(length=50), nullable=False, server_default="child_config"),
            sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("relationship_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["root_item_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["root_version_id"], ["meta_item_versions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    indexes = {idx.get("name") for idx in inspector.get_indexes("meta_baselines")}
    if "ix_meta_baselines_root_item_id" not in indexes:
        op.create_index(
            "ix_meta_baselines_root_item_id", "meta_baselines", ["root_item_id"]
        )
    if "ix_meta_baselines_root_version_id" not in indexes:
        op.create_index(
            "ix_meta_baselines_root_version_id",
            "meta_baselines",
            ["root_version_id"],
        )
    if "ix_meta_baselines_root_config_id" not in indexes:
        op.create_index(
            "ix_meta_baselines_root_config_id",
            "meta_baselines",
            ["root_config_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_baselines" not in inspector.get_table_names():
        return

    indexes = {idx.get("name") for idx in inspector.get_indexes("meta_baselines")}
    if "ix_meta_baselines_root_config_id" in indexes:
        op.drop_index("ix_meta_baselines_root_config_id", table_name="meta_baselines")
    if "ix_meta_baselines_root_version_id" in indexes:
        op.drop_index("ix_meta_baselines_root_version_id", table_name="meta_baselines")
    if "ix_meta_baselines_root_item_id" in indexes:
        op.drop_index("ix_meta_baselines_root_item_id", table_name="meta_baselines")

    op.drop_table("meta_baselines")
