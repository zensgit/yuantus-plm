"""
Document multi-site sync domain models.

Provides the data layer for managing remote sync sites and sync jobs
that track document replication across PLM site boundaries.

  - SyncSite   (meta_sync_sites)  – remote site / mirror endpoint
  - SyncJob    (meta_sync_jobs)   – a batch sync operation
  - SyncRecord (meta_sync_records)– per-document sync outcome within a job
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from yuantus.models.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SiteState(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ARCHIVED = "archived"


class SyncJobState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncDirection(str, enum.Enum):
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class SyncRecordOutcome(str, enum.Enum):
    SYNCED = "synced"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SyncSite(Base):
    """A remote PLM site / mirror endpoint for document sync."""

    __tablename__ = "meta_sync_sites"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Connection
    base_url = Column(String(500), nullable=True)
    site_code = Column(String(60), nullable=False, unique=True)
    state = Column(String(30), default=SiteState.ACTIVE.value, nullable=False)
    auth_type = Column(String(30), nullable=True)
    auth_config = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Capabilities
    direction = Column(
        String(30), default=SyncDirection.PUSH.value, nullable=False
    )
    is_primary = Column(Boolean, default=False, nullable=False)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Audit
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    jobs = relationship(
        "SyncJob", back_populates="site", cascade="all, delete-orphan"
    )


class SyncJob(Base):
    """A batch sync operation targeting a specific site."""

    __tablename__ = "meta_sync_jobs"

    id = Column(String, primary_key=True)
    site_id = Column(
        String,
        ForeignKey("meta_sync_sites.id"),
        nullable=False,
        index=True,
    )
    state = Column(
        String(30), default=SyncJobState.PENDING.value, nullable=False
    )
    direction = Column(
        String(30), default=SyncDirection.PUSH.value, nullable=False
    )

    # Scope
    document_filter = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    total_documents = Column(Integer, default=0, nullable=False)
    synced_count = Column(Integer, default=0, nullable=False)
    conflict_count = Column(Integer, default=0, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    skipped_count = Column(Integer, default=0, nullable=False)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Error
    error_message = Column(Text, nullable=True)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Audit
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Relationships
    site = relationship("SyncSite", back_populates="jobs")
    records = relationship(
        "SyncRecord", back_populates="job", cascade="all, delete-orphan"
    )


class SyncRecord(Base):
    """Per-document sync outcome within a job."""

    __tablename__ = "meta_sync_records"

    id = Column(String, primary_key=True)
    job_id = Column(
        String,
        ForeignKey("meta_sync_jobs.id"),
        nullable=False,
        index=True,
    )
    document_id = Column(String, nullable=False, index=True)

    # Checksums
    source_checksum = Column(String(128), nullable=True)
    target_checksum = Column(String(128), nullable=True)

    # Outcome
    outcome = Column(
        String(30), default=SyncRecordOutcome.SYNCED.value, nullable=False
    )
    conflict_detail = Column(Text, nullable=True)
    error_detail = Column(Text, nullable=True)

    # Audit
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job = relationship("SyncJob", back_populates="records")
