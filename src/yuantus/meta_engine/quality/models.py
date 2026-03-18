"""
Quality assurance domain models.

Mirrors Odoo 18 quality_control / quality_mrp concepts:
  - QualityPoint  (quality.point)   – defines *when* and *what* to check
  - QualityCheck  (quality.check)   – individual inspection instance
  - QualityAlert  (quality.alert)   – issue / non-conformance tracker
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


class QualityCheckType(str, enum.Enum):
    PASS_FAIL = "pass_fail"
    MEASURE = "measure"
    TAKE_PICTURE = "take_picture"
    WORKSHEET = "worksheet"
    INSTRUCTIONS = "instructions"


class QualityCheckResult(str, enum.Enum):
    NONE = "none"
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class QualityAlertState(str, enum.Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class QualityAlertPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class QualityPoint(Base):
    """Quality Control Point – the *template* that says when a check is needed.

    Equivalent to Odoo ``quality.point``.
    """

    __tablename__ = "meta_quality_points"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    title = Column(String(400), nullable=True)

    # What to check
    check_type = Column(
        String(30),
        default=QualityCheckType.PASS_FAIL.value,
        nullable=False,
    )

    # Scope: product / item-type / routing / operation
    product_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)
    item_type_id = Column(String, nullable=True, index=True)
    routing_id = Column(String, nullable=True, index=True)
    operation_id = Column(String, nullable=True, index=True)

    # Measure-specific thresholds
    measure_min = Column(Float, nullable=True)
    measure_max = Column(Float, nullable=True)
    measure_unit = Column(String(50), nullable=True)
    measure_tolerance = Column(Float, nullable=True)

    # Worksheet / instructions
    worksheet_template = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)

    # Trigger configuration
    trigger_on = Column(String(50), default="manual")  # manual | receipt | production | transfer
    is_active = Column(Boolean, default=True)
    sequence = Column(Integer, default=10)

    # Extensible properties
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Team assignment
    team_name = Column(String(200), nullable=True)
    responsible_user_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    checks = relationship("QualityCheck", back_populates="point", cascade="all, delete-orphan")


class QualityCheck(Base):
    """A single inspection instance created from a QualityPoint.

    Equivalent to Odoo ``quality.check``.
    """

    __tablename__ = "meta_quality_checks"

    id = Column(String, primary_key=True)
    point_id = Column(
        String,
        ForeignKey("meta_quality_points.id"),
        nullable=False,
        index=True,
    )
    product_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)

    # Manufacturing scope (copied from point on creation)
    routing_id = Column(String, nullable=True, index=True)
    operation_id = Column(String, nullable=True, index=True)

    # Check execution
    check_type = Column(String(30), nullable=False)
    result = Column(String(20), default=QualityCheckResult.NONE.value)
    measure_value = Column(Float, nullable=True)
    picture_path = Column(String, nullable=True)
    worksheet_data = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    note = Column(Text, nullable=True)

    # Context
    source_document_ref = Column(String(200), nullable=True)  # e.g. MO-00123
    lot_serial = Column(String(200), nullable=True)

    # State
    checked_at = Column(DateTime(timezone=True), nullable=True)
    checked_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    point = relationship("QualityPoint", back_populates="checks")
    alerts = relationship("QualityAlert", back_populates="check", cascade="all, delete-orphan")


class QualityAlert(Base):
    """Non-conformance / quality issue tracker.

    Equivalent to Odoo ``quality.alert``.
    """

    __tablename__ = "meta_quality_alerts"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    check_id = Column(
        String,
        ForeignKey("meta_quality_checks.id"),
        nullable=True,
        index=True,
    )
    product_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)

    # Alert details
    state = Column(String(30), default=QualityAlertState.NEW.value)
    priority = Column(String(20), default=QualityAlertPriority.MEDIUM.value)
    description = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)

    # Assignment
    team_name = Column(String(200), nullable=True)
    assigned_user_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    check = relationship("QualityCheck", back_populates="alerts")
