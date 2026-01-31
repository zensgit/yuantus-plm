"""add manufacturing tables

Revision ID: t1b2c3d4e6a8
Revises: s1b2c3d4e6a7
Create Date: 2026-01-31 15:55:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "t1b2c3d4e6a8"
down_revision: Union[str, None] = "s1b2c3d4e6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_workcenters" not in existing:
        op.create_table(
            "meta_workcenters",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("code", sa.String(length=120), nullable=False, unique=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("plant_code", sa.String(length=120), nullable=True),
            sa.Column("department_code", sa.String(length=120), nullable=True),
            sa.Column("capacity_per_day", sa.Float(), nullable=True, server_default="8.0"),
            sa.Column("efficiency", sa.Float(), nullable=True, server_default="1.0"),
            sa.Column("utilization", sa.Float(), nullable=True, server_default="0.9"),
            sa.Column("machine_count", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("worker_count", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("cost_center", sa.String(length=120), nullable=True),
            sa.Column("labor_rate", sa.Float(), nullable=True),
            sa.Column("overhead_rate", sa.Float(), nullable=True),
            sa.Column("scheduling_type", sa.String(length=50), nullable=True, server_default="finite"),
            sa.Column("queue_time_default", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "meta_manufacturing_boms" not in existing:
        op.create_table(
            "meta_manufacturing_boms",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("source_item_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("version", sa.String(length=50), nullable=True, server_default="1.0"),
            sa.Column("revision", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("bom_type", sa.String(length=20), nullable=True, server_default="mbom"),
            sa.Column("plant_code", sa.String(length=120), nullable=True),
            sa.Column("line_code", sa.String(length=120), nullable=True),
            sa.Column("effective_from", sa.DateTime(), nullable=True),
            sa.Column("effective_to", sa.DateTime(), nullable=True),
            sa.Column("state", sa.String(length=50), nullable=True, server_default="draft"),
            sa.Column(
                "structure",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("released_at", sa.DateTime(), nullable=True),
            sa.Column("released_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["source_item_id"], ["meta_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["released_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_routings" not in existing:
        op.create_table(
            "meta_routings",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("mbom_id", sa.String(length=36), nullable=True, index=True),
            sa.Column("item_id", sa.String(length=36), nullable=True, index=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("routing_code", sa.String(length=120), nullable=True, unique=True),
            sa.Column("version", sa.String(length=50), nullable=True, server_default="1.0"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("effective_from", sa.DateTime(), nullable=True),
            sa.Column("effective_to", sa.DateTime(), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("plant_code", sa.String(length=120), nullable=True),
            sa.Column("line_code", sa.String(length=120), nullable=True),
            sa.Column("state", sa.String(length=50), nullable=True, server_default="draft"),
            sa.Column("total_setup_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("total_run_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("total_labor_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["mbom_id"], ["meta_manufacturing_boms.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["item_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_operations" not in existing:
        op.create_table(
            "meta_operations",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("routing_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("operation_number", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("operation_type", sa.String(length=50), nullable=True, server_default="fabrication"),
            sa.Column("sequence", sa.Integer(), nullable=True, server_default="10"),
            sa.Column("workcenter_id", sa.String(length=36), nullable=True),
            sa.Column("workcenter_code", sa.String(length=120), nullable=True),
            sa.Column("setup_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("run_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("queue_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("move_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("wait_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("labor_setup_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("labor_run_time", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("crew_size", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("machines_required", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("overlap_quantity", sa.Integer(), nullable=True),
            sa.Column("transfer_batch", sa.Integer(), nullable=True),
            sa.Column("is_subcontracted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("subcontractor_id", sa.String(length=36), nullable=True),
            sa.Column("inspection_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("inspection_plan_id", sa.String(length=36), nullable=True),
            sa.Column("tooling_requirements", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True),
            sa.Column("work_instructions", sa.Text(), nullable=True),
            sa.Column("document_ids", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True),
            sa.Column("labor_cost_rate", sa.Float(), nullable=True),
            sa.Column("overhead_rate", sa.Float(), nullable=True),
            sa.Column("properties", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True),
            sa.ForeignKeyConstraint(["routing_id"], ["meta_routings.id"], ondelete="CASCADE"),
        )

    if "meta_mbom_lines" not in existing:
        op.create_table(
            "meta_mbom_lines",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("mbom_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("parent_line_id", sa.String(length=36), nullable=True),
            sa.Column("item_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("sequence", sa.Integer(), nullable=True, server_default="10"),
            sa.Column("level", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("quantity", sa.Numeric(20, 6), nullable=True, server_default="1"),
            sa.Column("unit", sa.String(length=50), nullable=True, server_default="EA"),
            sa.Column("ebom_relationship_id", sa.String(length=36), nullable=True),
            sa.Column("make_buy", sa.String(length=50), nullable=True, server_default="make"),
            sa.Column("supply_type", sa.String(length=120), nullable=True),
            sa.Column("operation_id", sa.String(length=36), nullable=True),
            sa.Column("backflush", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("scrap_rate", sa.Float(), nullable=True, server_default="0.0"),
            sa.Column("fixed_quantity", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("properties", sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True),
            sa.ForeignKeyConstraint(["mbom_id"], ["meta_manufacturing_boms.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_line_id"], ["meta_mbom_lines.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["item_id"], ["meta_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["ebom_relationship_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["operation_id"], ["meta_operations.id"], ondelete="SET NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_mbom_lines" in existing:
        op.drop_table("meta_mbom_lines")
    if "meta_operations" in existing:
        op.drop_table("meta_operations")
    if "meta_routings" in existing:
        op.drop_table("meta_routings")
    if "meta_manufacturing_boms" in existing:
        op.drop_table("meta_manufacturing_boms")
    if "meta_workcenters" in existing:
        op.drop_table("meta_workcenters")
