"""add parallel branch extension tables

Revision ID: z1b2c3d4e7a5
Revises: y1b2c3d4e7a4
Create Date: 2026-02-27 21:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z1b2c3d4e7a5"
down_revision: Union[str, None] = "y1b2c3d4e7a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _j() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_remote_sites" not in existing:
        op.create_table(
            "meta_remote_sites",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("endpoint", sa.String(length=500), nullable=False),
            sa.Column("auth_mode", sa.String(length=50), nullable=False),
            sa.Column("auth_secret_ciphertext", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("metadata_json", _j(), nullable=True),
            sa.Column("last_health_status", sa.String(length=30), nullable=True),
            sa.Column("last_health_error", sa.Text(), nullable=True),
            sa.Column("last_health_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(
            op.f("ix_meta_remote_sites_name"),
            "meta_remote_sites",
            ["name"],
            unique=False,
        )

    if "meta_eco_activity_gates" not in existing:
        op.create_table(
            "meta_eco_activity_gates",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("eco_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("assignee_id", sa.Integer(), nullable=True),
            sa.Column("depends_on_activity_ids", _j(), nullable=True),
            sa.Column("properties", _j(), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("closed_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["assignee_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["closed_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_eco_activity_gates_eco_id"),
            "meta_eco_activity_gates",
            ["eco_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_eco_activity_gates_status"),
            "meta_eco_activity_gates",
            ["status"],
            unique=False,
        )

    if "meta_eco_activity_gate_events" not in existing:
        op.create_table(
            "meta_eco_activity_gate_events",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("eco_id", sa.String(), nullable=False),
            sa.Column("activity_id", sa.String(), nullable=False),
            sa.Column("from_status", sa.String(length=30), nullable=True),
            sa.Column("to_status", sa.String(length=30), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_eco_activity_gate_events_eco_id"),
            "meta_eco_activity_gate_events",
            ["eco_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_eco_activity_gate_events_activity_id"),
            "meta_eco_activity_gate_events",
            ["activity_id"],
            unique=False,
        )

    if "meta_workflow_custom_action_rules" not in existing:
        op.create_table(
            "meta_workflow_custom_action_rules",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("target_object", sa.String(length=60), nullable=False),
            sa.Column("workflow_map_id", sa.String(), nullable=True),
            sa.Column("from_state", sa.String(length=120), nullable=True),
            sa.Column("to_state", sa.String(length=120), nullable=True),
            sa.Column("trigger_phase", sa.String(length=30), nullable=False),
            sa.Column("action_type", sa.String(length=80), nullable=False),
            sa.Column("action_params", _j(), nullable=True),
            sa.Column("fail_strategy", sa.String(length=30), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(
            op.f("ix_meta_workflow_custom_action_rules_workflow_map_id"),
            "meta_workflow_custom_action_rules",
            ["workflow_map_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_workflow_custom_action_rules_from_state"),
            "meta_workflow_custom_action_rules",
            ["from_state"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_workflow_custom_action_rules_to_state"),
            "meta_workflow_custom_action_rules",
            ["to_state"],
            unique=False,
        )

    if "meta_workflow_custom_action_runs" not in existing:
        op.create_table(
            "meta_workflow_custom_action_runs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("rule_id", sa.String(), nullable=False),
            sa.Column("object_id", sa.String(), nullable=False),
            sa.Column("target_object", sa.String(length=60), nullable=False),
            sa.Column("from_state", sa.String(length=120), nullable=True),
            sa.Column("to_state", sa.String(length=120), nullable=True),
            sa.Column("trigger_phase", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("result", _j(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_workflow_custom_action_runs_rule_id"),
            "meta_workflow_custom_action_runs",
            ["rule_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_workflow_custom_action_runs_object_id"),
            "meta_workflow_custom_action_runs",
            ["object_id"],
            unique=False,
        )

    if "meta_consumption_plans" not in existing:
        op.create_table(
            "meta_consumption_plans",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("state", sa.String(length=30), nullable=False),
            sa.Column("item_id", sa.String(), nullable=True),
            sa.Column("period_unit", sa.String(length=20), nullable=False),
            sa.Column("period_start", sa.DateTime(), nullable=True),
            sa.Column("period_end", sa.DateTime(), nullable=True),
            sa.Column("planned_quantity", sa.Float(), nullable=False, server_default="0"),
            sa.Column("uom", sa.String(length=20), nullable=False, server_default="EA"),
            sa.Column("properties", _j(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_consumption_plans_name"),
            "meta_consumption_plans",
            ["name"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_consumption_plans_state"),
            "meta_consumption_plans",
            ["state"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_consumption_plans_item_id"),
            "meta_consumption_plans",
            ["item_id"],
            unique=False,
        )

    if "meta_consumption_records" not in existing:
        op.create_table(
            "meta_consumption_records",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("plan_id", sa.String(), nullable=False),
            sa.Column("source_type", sa.String(length=60), nullable=False),
            sa.Column("source_id", sa.String(length=120), nullable=True),
            sa.Column("actual_quantity", sa.Float(), nullable=False, server_default="0"),
            sa.Column("recorded_at", sa.DateTime(), nullable=False),
            sa.Column("properties", _j(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_consumption_records_plan_id"),
            "meta_consumption_records",
            ["plan_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_consumption_records_source_id"),
            "meta_consumption_records",
            ["source_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_consumption_records_recorded_at"),
            "meta_consumption_records",
            ["recorded_at"],
            unique=False,
        )

    if "meta_breakage_incidents" not in existing:
        op.create_table(
            "meta_breakage_incidents",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("product_item_id", sa.String(), nullable=True),
            sa.Column("bom_line_item_id", sa.String(), nullable=True),
            sa.Column("production_order_id", sa.String(length=120), nullable=True),
            sa.Column("version_id", sa.String(), nullable=True),
            sa.Column("batch_code", sa.String(length=120), nullable=True),
            sa.Column("customer_name", sa.String(length=200), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("responsibility", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("severity", sa.String(length=30), nullable=False),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in [
            "product_item_id",
            "bom_line_item_id",
            "production_order_id",
            "version_id",
            "batch_code",
            "customer_name",
            "status",
            "severity",
        ]:
            op.create_index(
                op.f(f"ix_meta_breakage_incidents_{column}"),
                "meta_breakage_incidents",
                [column],
                unique=False,
            )

    if "meta_workorder_document_links" not in existing:
        op.create_table(
            "meta_workorder_document_links",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("routing_id", sa.String(), nullable=False),
            sa.Column("operation_id", sa.String(), nullable=True),
            sa.Column("document_item_id", sa.String(), nullable=False),
            sa.Column("inherit_to_children", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("visible_in_production", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "routing_id",
                "operation_id",
                "document_item_id",
                name="uq_workorder_doc_link_scope",
            ),
        )
        op.create_index(
            op.f("ix_meta_workorder_document_links_routing_id"),
            "meta_workorder_document_links",
            ["routing_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_workorder_document_links_operation_id"),
            "meta_workorder_document_links",
            ["operation_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_workorder_document_links_document_item_id"),
            "meta_workorder_document_links",
            ["document_item_id"],
            unique=False,
        )

    if "meta_3d_overlays" not in existing:
        op.create_table(
            "meta_3d_overlays",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_item_id", sa.String(), nullable=False),
            sa.Column("version_label", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=60), nullable=True),
            sa.Column("visibility_role", sa.String(length=120), nullable=True),
            sa.Column("part_refs", _j(), nullable=True),
            sa.Column("properties", _j(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("document_item_id"),
        )
        op.create_index(
            op.f("ix_meta_3d_overlays_document_item_id"),
            "meta_3d_overlays",
            ["document_item_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_3d_overlays_status"),
            "meta_3d_overlays",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_3d_overlays" in existing:
        op.drop_table("meta_3d_overlays")
    if "meta_workorder_document_links" in existing:
        op.drop_table("meta_workorder_document_links")
    if "meta_breakage_incidents" in existing:
        op.drop_table("meta_breakage_incidents")
    if "meta_consumption_records" in existing:
        op.drop_table("meta_consumption_records")
    if "meta_consumption_plans" in existing:
        op.drop_table("meta_consumption_plans")
    if "meta_workflow_custom_action_runs" in existing:
        op.drop_table("meta_workflow_custom_action_runs")
    if "meta_workflow_custom_action_rules" in existing:
        op.drop_table("meta_workflow_custom_action_rules")
    if "meta_eco_activity_gate_events" in existing:
        op.drop_table("meta_eco_activity_gate_events")
    if "meta_eco_activity_gates" in existing:
        op.drop_table("meta_eco_activity_gates")
    if "meta_remote_sites" in existing:
        op.drop_table("meta_remote_sites")
