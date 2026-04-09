"""Generic approvals domain models.

Provides a reusable approval workflow that can be attached to any
domain entity (ECO, purchase order, quality deviation, etc.).

  - ApprovalCategory  – taxonomy for grouping approval types
  - ApprovalRequest   – individual approval request with state machine
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from yuantus.models.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ApprovalState(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ApprovalRequestEventType(str, enum.Enum):
    CREATED = "created"
    TRANSITION = "transition"


class ApprovalCategory(Base):
    """Approval category / taxonomy node."""

    __tablename__ = "meta_approval_categories"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    parent_id = Column(
        String,
        ForeignKey("meta_approval_categories.id"),
        nullable=True,
        index=True,
    )
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    requests = relationship("ApprovalRequest", back_populates="category")


class ApprovalRequest(Base):
    """Generic approval request with state machine.

    Can reference any domain entity via ``entity_type`` + ``entity_id``.
    """

    __tablename__ = "meta_approval_requests"

    id = Column(String, primary_key=True)
    title = Column(String(300), nullable=False)
    category_id = Column(
        String,
        ForeignKey("meta_approval_categories.id"),
        nullable=True,
        index=True,
    )

    # What is being approved
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String, nullable=True, index=True)

    # State machine
    state = Column(String(30), default=ApprovalState.DRAFT.value, nullable=False)
    priority = Column(String(20), default=ApprovalPriority.NORMAL.value, nullable=False)
    description = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Assignment
    requested_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    decided_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    category = relationship("ApprovalCategory", back_populates="requests")
    events = relationship(
        "ApprovalRequestEvent",
        back_populates="request",
        cascade="all, delete-orphan",
    )


class ApprovalRequestEvent(Base):
    """Durable approval request audit event."""

    __tablename__ = "meta_approval_request_events"

    id = Column(String, primary_key=True)
    request_id = Column(
        String,
        ForeignKey("meta_approval_requests.id"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(30), nullable=False)
    transition_type = Column(String(30), nullable=True)
    from_state = Column(String(30), nullable=True)
    to_state = Column(String(30), nullable=False)
    note = Column(Text, nullable=True)
    actor_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request = relationship("ApprovalRequest", back_populates="events")
