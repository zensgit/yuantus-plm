"""add approvals and subcontract table foundation

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-10 00:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _j() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {ix.get("name") for ix in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns, unique=False)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_approval_categories" not in existing:
        op.create_table(
            "meta_approval_categories",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("parent_id", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["parent_id"], ["meta_approval_categories.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_approval_categories_parent_id"),
            "meta_approval_categories",
            ["parent_id"],
            unique=False,
        )

    if "meta_approval_requests" not in existing:
        op.create_table(
            "meta_approval_requests",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("title", sa.String(length=300), nullable=False),
            sa.Column("category_id", sa.String(), nullable=True),
            sa.Column("entity_type", sa.String(length=100), nullable=True),
            sa.Column("entity_id", sa.String(), nullable=True),
            sa.Column(
                "state",
                sa.String(length=30),
                nullable=False,
                server_default=sa.text("'draft'"),
            ),
            sa.Column(
                "priority",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'normal'"),
            ),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("requested_by_id", sa.Integer(), nullable=True),
            sa.Column("assigned_to_id", sa.Integer(), nullable=True),
            sa.Column("decided_by_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("properties", _j(), nullable=True),
            sa.ForeignKeyConstraint(["category_id"], ["meta_approval_categories.id"]),
            sa.ForeignKeyConstraint(["requested_by_id"], ["rbac_users.id"]),
            sa.ForeignKeyConstraint(["assigned_to_id"], ["rbac_users.id"]),
            sa.ForeignKeyConstraint(["decided_by_id"], ["rbac_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_approval_requests_category_id"),
            "meta_approval_requests",
            ["category_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_approval_requests_entity_type"),
            "meta_approval_requests",
            ["entity_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_approval_requests_entity_id"),
            "meta_approval_requests",
            ["entity_id"],
            unique=False,
        )

    if "meta_approval_request_events" not in existing:
        op.create_table(
            "meta_approval_request_events",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("request_id", sa.String(), nullable=False),
            sa.Column("event_type", sa.String(length=30), nullable=False),
            sa.Column("transition_type", sa.String(length=30), nullable=True),
            sa.Column("from_state", sa.String(length=30), nullable=True),
            sa.Column("to_state", sa.String(length=30), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("actor_id", sa.Integer(), nullable=True),
            sa.Column("properties", _j(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["request_id"], ["meta_approval_requests.id"]),
            sa.ForeignKeyConstraint(["actor_id"], ["rbac_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_approval_request_events_request_id"),
            "meta_approval_request_events",
            ["request_id"],
            unique=False,
        )

    if "meta_subcontract_orders" not in existing:
        op.create_table(
            "meta_subcontract_orders",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("item_id", sa.String(), nullable=True),
            sa.Column("routing_id", sa.String(), nullable=True),
            sa.Column("source_operation_id", sa.String(), nullable=True),
            sa.Column("vendor_id", sa.String(), nullable=True),
            sa.Column("vendor_name", sa.String(length=200), nullable=True),
            sa.Column(
                "state",
                sa.String(length=40),
                nullable=False,
                server_default=sa.text("'draft'"),
            ),
            sa.Column(
                "requested_qty",
                sa.Float(),
                nullable=False,
                server_default=sa.text("1.0"),
            ),
            sa.Column(
                "issued_qty",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
            sa.Column(
                "received_qty",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
            sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("properties", _j(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["item_id"], ["meta_items.id"]),
            sa.ForeignKeyConstraint(["source_operation_id"], ["meta_operations.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_subcontract_orders_item_id"),
            "meta_subcontract_orders",
            ["item_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_subcontract_orders_routing_id"),
            "meta_subcontract_orders",
            ["routing_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_subcontract_orders_source_operation_id"),
            "meta_subcontract_orders",
            ["source_operation_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_meta_subcontract_orders_vendor_id"),
            "meta_subcontract_orders",
            ["vendor_id"],
            unique=False,
        )

    if "meta_subcontract_order_events" not in existing:
        op.create_table(
            "meta_subcontract_order_events",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("order_id", sa.String(), nullable=False),
            sa.Column("event_type", sa.String(length=40), nullable=False),
            sa.Column(
                "quantity",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
            sa.Column("reference", sa.String(length=200), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("properties", _j(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["order_id"], ["meta_subcontract_orders.id"]),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_meta_subcontract_order_events_order_id"),
            "meta_subcontract_order_events",
            ["order_id"],
            unique=False,
        )

    _ensure_index(
        "meta_approval_categories",
        op.f("ix_meta_approval_categories_parent_id"),
        ["parent_id"],
    )
    _ensure_index(
        "meta_approval_requests",
        op.f("ix_meta_approval_requests_category_id"),
        ["category_id"],
    )
    _ensure_index(
        "meta_approval_requests",
        op.f("ix_meta_approval_requests_entity_type"),
        ["entity_type"],
    )
    _ensure_index(
        "meta_approval_requests",
        op.f("ix_meta_approval_requests_entity_id"),
        ["entity_id"],
    )
    _ensure_index(
        "meta_approval_request_events",
        op.f("ix_meta_approval_request_events_request_id"),
        ["request_id"],
    )
    _ensure_index(
        "meta_subcontract_orders",
        op.f("ix_meta_subcontract_orders_item_id"),
        ["item_id"],
    )
    _ensure_index(
        "meta_subcontract_orders",
        op.f("ix_meta_subcontract_orders_routing_id"),
        ["routing_id"],
    )
    _ensure_index(
        "meta_subcontract_orders",
        op.f("ix_meta_subcontract_orders_source_operation_id"),
        ["source_operation_id"],
    )
    _ensure_index(
        "meta_subcontract_orders",
        op.f("ix_meta_subcontract_orders_vendor_id"),
        ["vendor_id"],
    )
    _ensure_index(
        "meta_subcontract_order_events",
        op.f("ix_meta_subcontract_order_events_order_id"),
        ["order_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_subcontract_order_events" in existing:
        op.drop_index(
            op.f("ix_meta_subcontract_order_events_order_id"),
            table_name="meta_subcontract_order_events",
        )
        op.drop_table("meta_subcontract_order_events")

    if "meta_subcontract_orders" in existing:
        op.drop_index(op.f("ix_meta_subcontract_orders_vendor_id"), table_name="meta_subcontract_orders")
        op.drop_index(
            op.f("ix_meta_subcontract_orders_source_operation_id"),
            table_name="meta_subcontract_orders",
        )
        op.drop_index(op.f("ix_meta_subcontract_orders_routing_id"), table_name="meta_subcontract_orders")
        op.drop_index(op.f("ix_meta_subcontract_orders_item_id"), table_name="meta_subcontract_orders")
        op.drop_table("meta_subcontract_orders")

    if "meta_approval_request_events" in existing:
        op.drop_index(
            op.f("ix_meta_approval_request_events_request_id"),
            table_name="meta_approval_request_events",
        )
        op.drop_table("meta_approval_request_events")

    if "meta_approval_requests" in existing:
        op.drop_index(op.f("ix_meta_approval_requests_entity_id"), table_name="meta_approval_requests")
        op.drop_index(op.f("ix_meta_approval_requests_entity_type"), table_name="meta_approval_requests")
        op.drop_index(op.f("ix_meta_approval_requests_category_id"), table_name="meta_approval_requests")
        op.drop_table("meta_approval_requests")

    if "meta_approval_categories" in existing:
        op.drop_index(
            op.f("ix_meta_approval_categories_parent_id"),
            table_name="meta_approval_categories",
        )
        op.drop_table("meta_approval_categories")
