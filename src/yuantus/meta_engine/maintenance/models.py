"""
Maintenance domain models.

Mirrors Odoo 18 maintenance module concepts:
  - Equipment        (maintenance.equipment)      – physical asset register
  - MaintenanceRequest (maintenance.request)       – work request / work order
  - MaintenanceTeam  (maintenance.team)            – team assignment
  - MaintenanceCategory (maintenance.equipment.category) – equipment taxonomy
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


class EquipmentStatus(str, enum.Enum):
    OPERATIONAL = "operational"
    IN_MAINTENANCE = "in_maintenance"
    OUT_OF_SERVICE = "out_of_service"
    DECOMMISSIONED = "decommissioned"


class MaintenanceRequestState(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class MaintenanceRequestPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MaintenanceType(str, enum.Enum):
    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    PREDICTIVE = "predictive"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class MaintenanceCategory(Base):
    """Equipment category / taxonomy node."""

    __tablename__ = "meta_maintenance_categories"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    parent_id = Column(
        String,
        ForeignKey("meta_maintenance_categories.id"),
        nullable=True,
        index=True,
    )
    description = Column(Text, nullable=True)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    equipment = relationship("Equipment", back_populates="category")


class Equipment(Base):
    """Physical asset / equipment register entry.

    Equivalent to Odoo ``maintenance.equipment``.
    """

    __tablename__ = "meta_maintenance_equipment"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    serial_number = Column(String(200), nullable=True, unique=True)
    model = Column(String(200), nullable=True)
    manufacturer = Column(String(200), nullable=True)

    # Classification
    category_id = Column(
        String,
        ForeignKey("meta_maintenance_categories.id"),
        nullable=True,
        index=True,
    )
    status = Column(
        String(30),
        default=EquipmentStatus.OPERATIONAL.value,
        nullable=False,
    )

    # Location
    location = Column(String(400), nullable=True)
    plant_code = Column(String(120), nullable=True)
    workcenter_id = Column(String, nullable=True)

    # Lifecycle
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    warranty_expiry = Column(DateTime(timezone=True), nullable=True)
    expected_mtbf_days = Column(Float, nullable=True)  # mean time between failures

    # Assignment
    owner_user_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    team_name = Column(String(200), nullable=True)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    category = relationship("MaintenanceCategory", back_populates="equipment")
    requests = relationship(
        "MaintenanceRequest", back_populates="equipment", cascade="all, delete-orphan"
    )


class MaintenanceRequest(Base):
    """Maintenance work request / work order.

    Equivalent to Odoo ``maintenance.request``.
    """

    __tablename__ = "meta_maintenance_requests"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    equipment_id = Column(
        String,
        ForeignKey("meta_maintenance_equipment.id"),
        nullable=False,
        index=True,
    )

    # Request details
    maintenance_type = Column(
        String(30),
        default=MaintenanceType.CORRECTIVE.value,
        nullable=False,
    )
    state = Column(String(30), default=MaintenanceRequestState.DRAFT.value, nullable=False)
    priority = Column(
        String(20),
        default=MaintenanceRequestPriority.MEDIUM.value,
        nullable=False,
    )
    description = Column(Text, nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Scheduling
    scheduled_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Float, nullable=True)

    # Assignment
    assigned_user_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    team_name = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    equipment = relationship("Equipment", back_populates="requests")
