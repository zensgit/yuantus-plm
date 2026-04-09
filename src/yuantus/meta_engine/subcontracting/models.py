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
    ORDER_CREATED = "order_created"
    VENDOR_ASSIGNED = "vendor_assigned"
    VENDOR_MESSAGE = "vendor_message"
    VENDOR_MESSAGE_RESOLUTION = "vendor_message_resolution"
    VENDOR_MESSAGE_ASSIGNMENT = "vendor_message_assignment"
    VENDOR_MESSAGE_ROLLBACK_ATTEMPT = "vendor_message_rollback_attempt"
    VENDOR_MESSAGE_ESCALATION = "vendor_message_escalation"
    VENDOR_MESSAGE_SLA_CONTROL = "vendor_message_sla_control"
    VENDOR_MESSAGE_ALERT_CONTROL = "vendor_message_alert_control"
    VENDOR_ACKNOWLEDGED = "vendor_acknowledged"
    VENDOR_RESPONSE = "vendor_response"
    VENDOR_CONFIRMATION = "vendor_confirmation"
    VENDOR_COMMITMENT = "vendor_commitment"
    VENDOR_PROPOSAL_REVIEW = "vendor_proposal_review"
    VENDOR_PACKET_CONTEXT_UPDATED = "vendor_packet_context_updated"
    MATERIAL_ISSUE = "material_issue"
    RECEIPT = "receipt"
    RECEIPT_RETURN = "receipt_return"
    RECEIPT_RETURN_DISPOSITION = "receipt_return_disposition"
    RECEIPT_RETURN_DISPOSITION_APPROVAL = "receipt_return_disposition_approval"
    RECEIPT_RETURN_DISPOSITION_APPROVAL_ASSIGNMENT = (
        "receipt_return_disposition_approval_assignment"
    )
    RECEIPT_RETURN_DISPOSITION_APPROVAL_HANDOFF = (
        "receipt_return_disposition_approval_handoff"
    )
    RECEIPT_RETURN_DISPOSITION_APPROVAL_OVERRIDE = (
        "receipt_return_disposition_approval_override"
    )
    CANCELLED = "cancelled"
    REOPENED = "reopened"


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
