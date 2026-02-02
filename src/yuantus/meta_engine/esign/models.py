"""
Electronic signature data models (21 CFR Part 11 / EU Annex 11 aligned).
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from yuantus.models.base import Base


class SignatureMeaning(str, enum.Enum):
    AUTHORED = "authored"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    RELEASED = "released"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ACKNOWLEDGED = "acknowledged"
    WITNESSED = "witnessed"


class SignatureStatus(str, enum.Enum):
    VALID = "valid"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SigningReason(Base):
    __tablename__ = "meta_signing_reasons"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    meaning = Column(String, default=SignatureMeaning.APPROVED.value)

    regulatory_reference = Column(String, nullable=True)

    item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)

    from_state = Column(String, nullable=True)
    to_state = Column(String, nullable=True)

    requires_password = Column(Boolean, default=True)
    requires_comment = Column(Boolean, default=False)

    sequence = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ElectronicSignature(Base):
    __tablename__ = "meta_electronic_signatures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    item_generation = Column(Integer, nullable=False)

    signer_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=False)
    signer_username = Column(String, nullable=False)
    signer_full_name = Column(String, nullable=False)

    reason_id = Column(String, ForeignKey("meta_signing_reasons.id"), nullable=True)
    meaning = Column(String, nullable=False)
    reason_text = Column(String, nullable=True)

    comment = Column(Text, nullable=True)

    signed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    signature_hash = Column(String, nullable=False)
    content_hash = Column(String, nullable=False)

    client_ip = Column(String, nullable=True)
    client_info = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    status = Column(String, default=SignatureStatus.VALID.value)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    workflow_instance_id = Column(String, nullable=True)
    workflow_activity_id = Column(String, nullable=True)


class SignatureManifest(Base):
    __tablename__ = "meta_signature_manifests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    item_generation = Column(Integer, nullable=False)

    required_signatures = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    is_complete = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    manifest_hash = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SignatureAuditLog(Base):
    __tablename__ = "meta_signature_audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    action = Column(String, nullable=False)

    signature_id = Column(String, ForeignKey("meta_electronic_signatures.id"), nullable=True)
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)

    actor_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=False)
    actor_username = Column(String, nullable=False)

    details = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    client_ip = Column(String, nullable=True)
