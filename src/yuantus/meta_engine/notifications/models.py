from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from yuantus.models.base import Base


class NotificationOutboxState(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"


class NotificationDeliveryState(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationDeliveryReason(str, enum.Enum):
    RECIPIENT_MISSING = "recipient_missing"
    ADAPTER_ERROR = "adapter_error"
    REMOTE_ERROR = "remote_error"
    VALIDATION_ERROR = "validation_error"


class NotificationOutbox(Base):
    """One durable logical notification event.

    A notification is not a delivery. The event row stores the immutable payload
    snapshot and idempotency identity; delivery rows fan out per recipient/channel.
    """

    __tablename__ = "meta_notification_outbox"

    id = Column(String, primary_key=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    org_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(120), nullable=False, index=True)
    object_type = Column(String(120), nullable=True)
    object_id = Column(String, nullable=True, index=True)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    payload_fingerprint = Column(String(128), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    state = Column(
        String(30), default=NotificationOutboxState.PENDING.value, nullable=False
    )
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", name="uq_notification_outbox_idempotency_key"
        ),
    )


class NotificationDelivery(Base):
    """One recipient/channel delivery for a logical notification."""

    __tablename__ = "meta_notification_deliveries"

    id = Column(String, primary_key=True)
    notification_id = Column(
        String,
        ForeignKey("meta_notification_outbox.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(String(64), nullable=True, index=True)
    org_id = Column(String(64), nullable=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    recipient_key = Column(String(200), nullable=False)
    recipient_email = Column(String(255), nullable=True)
    channel = Column(String(30), default="email", nullable=False)
    state = Column(
        String(30), default=NotificationDeliveryState.PENDING.value, nullable=False
    )
    reason = Column(String(30), nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    remote_id = Column(String, nullable=True)
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    next_attempt_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    worker_id = Column(String, nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "recipient_key",
            "channel",
            name="uq_notification_delivery_recipient_channel",
        ),
    )

