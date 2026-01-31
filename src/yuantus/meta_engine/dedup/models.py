"""Models for CAD deduplication management."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
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


class SimilarityStatus(str, enum.Enum):
    """Similarity record status."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    MERGED = "merged"
    IGNORED = "ignored"


class DedupBatchStatus(str, enum.Enum):
    """Batch dedup job status."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimilarityRecord(Base):
    """Similarity record between two CAD files."""

    __tablename__ = "meta_similarity_records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    source_file_id = Column(String, ForeignKey("meta_files.id"), nullable=False, index=True)
    target_file_id = Column(String, ForeignKey("meta_files.id"), nullable=False, index=True)

    similarity_score = Column(Float, nullable=False)
    similarity_type = Column(String, default="visual")
    detection_method = Column(String)
    detection_params = Column(JSON().with_variant(JSONB, "postgresql"))

    status = Column(String, default=SimilarityStatus.PENDING.value, index=True)

    reviewed_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_comment = Column(Text, nullable=True)

    relationship_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)
    batch_id = Column(String, ForeignKey("meta_dedup_batches.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    source_file = relationship("FileContainer", foreign_keys=[source_file_id])
    target_file = relationship("FileContainer", foreign_keys=[target_file_id])
    reviewed_by = relationship("RBACUser", foreign_keys=[reviewed_by_id])


class DedupRule(Base):
    """Deduplication rule configuration."""

    __tablename__ = "meta_dedup_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)

    item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)
    document_type = Column(String, nullable=True)

    phash_threshold = Column(Integer, default=10)
    feature_threshold = Column(Float, default=0.85)
    combined_threshold = Column(Float, default=0.80)
    detection_mode = Column(String, default="balanced")

    auto_create_relationship = Column(Boolean, default=False)
    auto_trigger_workflow = Column(Boolean, default=False)
    workflow_map_id = Column(String, ForeignKey("meta_workflow_maps.id"), nullable=True)

    exclude_patterns = Column(JSON().with_variant(JSONB, "postgresql"))
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DedupBatch(Base):
    """Batch deduplication task tracking."""

    __tablename__ = "meta_dedup_batches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String)
    description = Column(Text)

    scope_type = Column(String, default="all")
    scope_config = Column(JSON().with_variant(JSONB, "postgresql"))

    rule_id = Column(String, ForeignKey("meta_dedup_rules.id"), nullable=True)

    status = Column(String, default=DedupBatchStatus.QUEUED.value, index=True)

    total_files = Column(Integer, default=0)
    processed_files = Column(Integer, default=0)
    found_similarities = Column(Integer, default=0)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    summary = Column(JSON().with_variant(JSONB, "postgresql"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    rule = relationship("DedupRule", foreign_keys=[rule_id])
    created_by = relationship("RBACUser", foreign_keys=[created_by_id])
    records = relationship("SimilarityRecord", backref="batch", foreign_keys="SimilarityRecord.batch_id")
