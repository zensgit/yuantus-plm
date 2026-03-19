"""
Cutted-parts domain models.

Provides the data layer for managing raw materials, cutting plans,
and individual cut results with waste/usage tracking.

  - RawMaterial  (meta_raw_materials)  – stock material available for cutting
  - CutPlan      (meta_cut_plans)      – a cutting plan / nesting job
  - CutResult    (meta_cut_results)    – individual cut piece outcome
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


class MaterialType(str, enum.Enum):
    SHEET = "sheet"
    BAR = "bar"
    TUBE = "tube"
    COIL = "coil"
    PLATE = "plate"


class CutPlanState(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CutResultStatus(str, enum.Enum):
    OK = "ok"
    SCRAP = "scrap"
    REWORK = "rework"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class RawMaterial(Base):
    """Stock material available for cutting operations."""

    __tablename__ = "meta_raw_materials"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    material_type = Column(
        String(30), default=MaterialType.SHEET.value, nullable=False
    )
    grade = Column(String(100), nullable=True)

    # Dimensions
    length = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    thickness = Column(Float, nullable=True)
    dimension_unit = Column(String(20), default="mm", nullable=False)

    # Stock
    weight_per_unit = Column(Float, nullable=True)
    weight_unit = Column(String(20), default="kg", nullable=False)
    stock_quantity = Column(Float, default=0.0, nullable=False)
    cost_per_unit = Column(Float, nullable=True)

    # Product link
    product_id = Column(
        String, ForeignKey("meta_items.id"), nullable=True, index=True
    )

    is_active = Column(Boolean, default=True, nullable=False)
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Audit
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class CutPlan(Base):
    """A cutting plan / nesting job that produces parts from raw material."""

    __tablename__ = "meta_cut_plans"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    state = Column(
        String(30), default=CutPlanState.DRAFT.value, nullable=False
    )

    # Material reference
    material_id = Column(
        String, ForeignKey("meta_raw_materials.id"), nullable=True, index=True
    )
    material_quantity = Column(Float, default=1.0, nullable=False)

    # Metrics (populated as cuts complete)
    total_parts = Column(Integer, default=0, nullable=False)
    ok_count = Column(Integer, default=0, nullable=False)
    scrap_count = Column(Integer, default=0, nullable=False)
    rework_count = Column(Integer, default=0, nullable=False)
    waste_pct = Column(Float, nullable=True)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Audit
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    cuts = relationship(
        "CutResult", back_populates="plan", cascade="all, delete-orphan"
    )


class CutResult(Base):
    """Individual cut piece outcome within a cutting plan."""

    __tablename__ = "meta_cut_results"

    id = Column(String, primary_key=True)
    plan_id = Column(
        String,
        ForeignKey("meta_cut_plans.id"),
        nullable=False,
        index=True,
    )
    part_id = Column(
        String, ForeignKey("meta_items.id"), nullable=True, index=True
    )

    # Geometry
    length = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    quantity = Column(Float, default=1.0, nullable=False)

    # Outcome
    status = Column(
        String(30), default=CutResultStatus.OK.value, nullable=False
    )
    scrap_weight = Column(Float, nullable=True)
    note = Column(Text, nullable=True)

    # Audit
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    plan = relationship("CutPlan", back_populates="cuts")
