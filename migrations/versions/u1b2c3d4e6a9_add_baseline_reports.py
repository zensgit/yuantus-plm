"""add baseline enhancements and reporting tables

Revision ID: u1b2c3d4e6a9
Revises: t1b2c3d4e6a8
Create Date: 2026-02-01 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "u1b2c3d4e6a9"
down_revision: Union[str, None] = "t1b2c3d4e6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    dialect = bind.dialect.name

    if "meta_baselines" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("meta_baselines")}

        def _add_columns(op_target, use_batch: bool = False):
            if "baseline_number" not in columns:
                op_target.add_column(
                    sa.Column("baseline_number", sa.String(length=60), nullable=True)
                )
            if "scope" not in columns:
                op_target.add_column(
                    sa.Column(
                        "scope", sa.String(length=50), nullable=True, server_default="product"
                    )
                )
            if "eco_id" not in columns:
                if use_batch:
                    op_target.add_column(sa.Column("eco_id", sa.String(), nullable=True))
                    op_target.create_foreign_key(
                        "fk_meta_baselines_eco_id_meta_items",
                        "meta_items",
                        ["eco_id"],
                        ["id"],
                        ondelete="SET NULL",
                    )
                else:
                    op_target.add_column(
                        sa.Column(
                            "eco_id",
                            sa.String(),
                            sa.ForeignKey("meta_items.id", ondelete="SET NULL"),
                            nullable=True,
                        )
                    )
            if "include_bom" not in columns:
                op_target.add_column(
                    sa.Column(
                        "include_bom",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("true"),
                    )
                )
            if "include_documents" not in columns:
                op_target.add_column(
                    sa.Column(
                        "include_documents",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("true"),
                    )
                )
            if "include_relationships" not in columns:
                op_target.add_column(
                    sa.Column(
                        "include_relationships",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("true"),
                    )
                )
            if "state" not in columns:
                op_target.add_column(
                    sa.Column(
                        "state", sa.String(length=50), nullable=True, server_default="draft"
                    )
                )
            if "is_validated" not in columns:
                op_target.add_column(
                    sa.Column(
                        "is_validated",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("false"),
                    )
                )
            if "validation_errors" not in columns:
                op_target.add_column(
                    sa.Column(
                        "validation_errors",
                        sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                        nullable=True,
                    )
                )
            if "validated_at" not in columns:
                op_target.add_column(sa.Column("validated_at", sa.DateTime(), nullable=True))
            if "validated_by_id" not in columns:
                if use_batch:
                    op_target.add_column(
                        sa.Column("validated_by_id", sa.Integer(), nullable=True)
                    )
                    op_target.create_foreign_key(
                        "fk_meta_baselines_validated_by_id_rbac_users",
                        "rbac_users",
                        ["validated_by_id"],
                        ["id"],
                        ondelete="SET NULL",
                    )
                else:
                    op_target.add_column(
                        sa.Column(
                            "validated_by_id",
                            sa.Integer(),
                            sa.ForeignKey("rbac_users.id", ondelete="SET NULL"),
                            nullable=True,
                        )
                    )
            if "is_locked" not in columns:
                op_target.add_column(
                    sa.Column(
                        "is_locked",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("false"),
                    )
                )
            if "locked_at" not in columns:
                op_target.add_column(sa.Column("locked_at", sa.DateTime(), nullable=True))
            if "released_at" not in columns:
                op_target.add_column(sa.Column("released_at", sa.DateTime(), nullable=True))
            if "released_by_id" not in columns:
                if use_batch:
                    op_target.add_column(
                        sa.Column("released_by_id", sa.Integer(), nullable=True)
                    )
                    op_target.create_foreign_key(
                        "fk_meta_baselines_released_by_id_rbac_users",
                        "rbac_users",
                        ["released_by_id"],
                        ["id"],
                        ondelete="SET NULL",
                    )
                else:
                    op_target.add_column(
                        sa.Column(
                            "released_by_id",
                            sa.Integer(),
                            sa.ForeignKey("rbac_users.id", ondelete="SET NULL"),
                            nullable=True,
                        )
                    )

        if dialect == "sqlite":
            with op.batch_alter_table("meta_baselines") as batch_op:
                _add_columns(batch_op, use_batch=True)
        else:
            _add_columns(op)

        indexes = {idx.get("name") for idx in inspector.get_indexes("meta_baselines")}
        if "ix_meta_baselines_baseline_number" not in indexes:
            op.create_index(
                "ix_meta_baselines_baseline_number",
                "meta_baselines",
                ["baseline_number"],
                unique=True,
            )

    if "meta_baseline_members" not in existing_tables:
        op.create_table(
            "meta_baseline_members",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("baseline_id", sa.String(), nullable=False, index=True),
            sa.Column("item_id", sa.String(), nullable=True, index=True),
            sa.Column("document_id", sa.String(), nullable=True, index=True),
            sa.Column("relationship_id", sa.String(), nullable=True, index=True),
            sa.Column("item_number", sa.String(), nullable=True),
            sa.Column("item_revision", sa.String(), nullable=True),
            sa.Column("item_generation", sa.Integer(), nullable=True),
            sa.Column("item_type", sa.String(), nullable=True),
            sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("path", sa.String(), nullable=True),
            sa.Column("quantity", sa.String(), nullable=True),
            sa.Column("member_type", sa.String(), nullable=False, server_default="item"),
            sa.Column("item_state", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["baseline_id"], ["meta_baselines.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["item_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["document_id"], ["meta_files.id"], ondelete="SET NULL"),
        )

    if "meta_baseline_comparisons" not in existing_tables:
        op.create_table(
            "meta_baseline_comparisons",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("baseline_a_id", sa.String(), nullable=False),
            sa.Column("baseline_b_id", sa.String(), nullable=False),
            sa.Column("added_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("removed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("changed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("unchanged_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "differences",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("compared_at", sa.DateTime(), nullable=True),
            sa.Column("compared_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["baseline_a_id"], ["meta_baselines.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["baseline_b_id"], ["meta_baselines.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["compared_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_saved_searches" not in existing_tables:
        op.create_table(
            "meta_saved_searches",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("item_type_id", sa.String(), nullable=True),
            sa.Column(
                "criteria",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=False,
            ),
            sa.Column(
                "display_columns",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("page_size", sa.Integer(), nullable=False, server_default="25"),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["item_type_id"], ["meta_item_types.id"], ondelete="SET NULL"),
        )

    if "meta_report_definitions" not in existing_tables:
        op.create_table(
            "meta_report_definitions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("code", sa.String(), nullable=True, unique=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("report_type", sa.String(), nullable=False, server_default="table"),
            sa.Column(
                "data_source",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=False,
            ),
            sa.Column(
                "layout",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column(
                "parameters",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column(
                "allowed_roles",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_report_executions" not in existing_tables:
        op.create_table(
            "meta_report_executions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("report_id", sa.String(), nullable=False, index=True),
            sa.Column(
                "parameters_used",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("status", sa.String(), nullable=False, server_default="running"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("row_count", sa.Integer(), nullable=True),
            sa.Column("execution_time_ms", sa.Integer(), nullable=True),
            sa.Column("export_format", sa.String(), nullable=True),
            sa.Column("export_path", sa.String(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.Column("executed_by_id", sa.Integer(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["report_id"], ["meta_report_definitions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["executed_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_dashboards" not in existing_tables:
        op.create_table(
            "meta_dashboards",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "layout",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column(
                "widgets",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("auto_refresh", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("refresh_interval", sa.Integer(), nullable=False, server_default="300"),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["owner_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "meta_dashboards" in existing_tables:
        op.drop_table("meta_dashboards")

    if "meta_report_executions" in existing_tables:
        op.drop_table("meta_report_executions")

    if "meta_report_definitions" in existing_tables:
        op.drop_table("meta_report_definitions")

    if "meta_saved_searches" in existing_tables:
        op.drop_table("meta_saved_searches")

    if "meta_baseline_comparisons" in existing_tables:
        op.drop_table("meta_baseline_comparisons")

    if "meta_baseline_members" in existing_tables:
        op.drop_table("meta_baseline_members")

    if "meta_baselines" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("meta_baselines")}
        indexes = {idx.get("name") for idx in inspector.get_indexes("meta_baselines")}

        if "ix_meta_baselines_baseline_number" in indexes:
            op.drop_index("ix_meta_baselines_baseline_number", table_name="meta_baselines")

        for column in [
            "released_by_id",
            "released_at",
            "locked_at",
            "is_locked",
            "validated_by_id",
            "validated_at",
            "validation_errors",
            "is_validated",
            "state",
            "include_relationships",
            "include_documents",
            "include_bom",
            "eco_id",
            "scope",
            "baseline_number",
        ]:
            if column in columns:
                op.drop_column("meta_baselines", column)
