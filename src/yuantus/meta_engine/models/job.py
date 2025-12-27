"""
Job Management Models
Tracks asynchronous background tasks.
Phase 4: Conversion Orchestration
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from yuantus.models.base import Base
import enum


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversionJob(Base):
    """
    Represents a background processing job.
    """

    __tablename__ = "meta_conversion_jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Task Info
    task_type = Column(
        String(50), nullable=False
    )  # e.g. "cad_conversion", "report_generation"
    payload = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )  # Arguments for the task

    # Status
    status = Column(String(20), default=JobStatus.PENDING.value, index=True)
    priority = Column(Integer, default=10)  # Higher is more urgent

    # Execution Info
    worker_id = Column(String(100), nullable=True)  # ID of the worker processing this
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(Text, nullable=True)
    dedupe_key = Column(String(120), nullable=True, index=True)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime, default=datetime.utcnow)  # Run after this time
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_by_id = Column(Integer, nullable=True)
