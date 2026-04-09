"""Subcontracting bootstrap models."""
from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from yuantus.models.base import Base


class SubcontractOrderState(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_RECEIVED = "partially_received"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SubcontractEventType(str, enum.Enum):
    MATERIAL_ISSUE = "material_issue"
    RECEIPT = "receipt"


class SubcontractOrder(Base):
    __tablename__ = "meta_subcontract_orders"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)
    routing_id = Column(String, nullable=True, index=True)
    source_operation_id = Column(String, ForeignKey("meta_operations.id"), nullable=True, index=True)
    vendor_id = Column(String, nullable=True, index=True)
    vendor_name = Column(String(200), nullable=True)
    state = Column(String(40), default=SubcontractOrderState.DRAFT.value, nullable=False)
    requested_qty = Column(Float, default=1.0, nullable=False)
    issued_qty = Column(Float, default=0.0, nullable=False)
    received_qty = Column(Float, default=0.0, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    note = Column(Text, nullable=True)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)


class SubcontractOrderEvent(Base):
    __tablename__ = "meta_subcontract_order_events"

    id = Column(String, primary_key=True)
    order_id = Column(String, ForeignKey("meta_subcontract_orders.id"), nullable=False, index=True)
    event_type = Column(String(40), nullable=False)
    quantity = Column(Float, default=0.0, nullable=False)
    reference = Column(String(200), nullable=True)
    note = Column(Text, nullable=True)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)


class SubcontractApprovalRoleMapping(Base):
    __tablename__ = "meta_subcontract_approval_role_mappings"

    id = Column(String, primary_key=True)
    role_code = Column(String(100), nullable=False, index=True)
    scope_type = Column(String(30), nullable=False, index=True)
    scope_value = Column(String(200), nullable=True, index=True)
    owner = Column(String(200), nullable=True)
    team = Column(String(200), nullable=True)
    required = Column(Boolean, default=False, nullable=False)
    sequence = Column(Integer, default=10, nullable=False)
    fallback_role = Column(String(100), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
