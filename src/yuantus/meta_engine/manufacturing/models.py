"""
Manufacturing domain models (MBOM + Routing).
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
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from yuantus.models.base import Base


class BOMType(str, enum.Enum):
    EBOM = "ebom"
    MBOM = "mbom"
    SBOM = "sbom"


class OperationType(str, enum.Enum):
    FABRICATION = "fabrication"
    ASSEMBLY = "assembly"
    INSPECTION = "inspection"
    TREATMENT = "treatment"
    PACKAGING = "packaging"


class ManufacturingBOM(Base):
    __tablename__ = "meta_manufacturing_boms"

    id = Column(String, primary_key=True)
    source_item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    version = Column(String(50), default="1.0")
    revision = Column(Integer, default=1)
    bom_type = Column(String(20), default=BOMType.MBOM.value)
    plant_code = Column(String(120), nullable=True)
    line_code = Column(String(120), nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    state = Column(String(50), default="draft")
    structure = Column(JSON().with_variant(JSONB, "postgresql"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    routings = relationship("Routing", back_populates="mbom")
    lines = relationship("MBOMLine", backref="mbom", cascade="all, delete-orphan")


class MBOMLine(Base):
    __tablename__ = "meta_mbom_lines"

    id = Column(String, primary_key=True)
    mbom_id = Column(String, ForeignKey("meta_manufacturing_boms.id"), nullable=False, index=True)
    parent_line_id = Column(String, ForeignKey("meta_mbom_lines.id"), nullable=True)
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    sequence = Column(Integer, default=10)
    level = Column(Integer, default=0)
    quantity = Column(Numeric(20, 6), default=1)
    unit = Column(String(50), default="EA")
    ebom_relationship_id = Column(String, ForeignKey("meta_items.id"), nullable=True)
    make_buy = Column(String(50), default="make")
    supply_type = Column(String(120), nullable=True)
    operation_id = Column(String, ForeignKey("meta_operations.id"), nullable=True)
    backflush = Column(Boolean, default=False)
    scrap_rate = Column(Float, default=0.0)
    fixed_quantity = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    properties = Column(JSON().with_variant(JSONB, "postgresql"))


class Routing(Base):
    __tablename__ = "meta_routings"

    id = Column(String, primary_key=True)
    mbom_id = Column(String, ForeignKey("meta_manufacturing_boms.id"), nullable=True, index=True)
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    routing_code = Column(String(120), unique=True, nullable=True)
    version = Column(String(50), default="1.0")
    description = Column(Text, nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    is_primary = Column(Boolean, default=True)
    plant_code = Column(String(120), nullable=True)
    line_code = Column(String(120), nullable=True)
    state = Column(String(50), default="draft")
    total_setup_time = Column(Float, default=0.0)
    total_run_time = Column(Float, default=0.0)
    total_labor_time = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    mbom = relationship("ManufacturingBOM", back_populates="routings")
    operations = relationship(
        "Operation",
        back_populates="routing",
        order_by="Operation.sequence",
        cascade="all, delete-orphan",
    )


class Operation(Base):
    __tablename__ = "meta_operations"

    id = Column(String, primary_key=True)
    routing_id = Column(String, ForeignKey("meta_routings.id"), nullable=False, index=True)
    operation_number = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    operation_type = Column(String(50), default=OperationType.FABRICATION.value)
    sequence = Column(Integer, default=10)
    workcenter_id = Column(String, nullable=True)
    workcenter_code = Column(String(120), nullable=True)
    setup_time = Column(Float, default=0.0)
    run_time = Column(Float, default=0.0)
    queue_time = Column(Float, default=0.0)
    move_time = Column(Float, default=0.0)
    wait_time = Column(Float, default=0.0)
    labor_setup_time = Column(Float, default=0.0)
    labor_run_time = Column(Float, default=0.0)
    crew_size = Column(Integer, default=1)
    machines_required = Column(Integer, default=1)
    overlap_quantity = Column(Integer, nullable=True)
    transfer_batch = Column(Integer, nullable=True)
    is_subcontracted = Column(Boolean, default=False)
    subcontractor_id = Column(String, nullable=True)
    inspection_required = Column(Boolean, default=False)
    inspection_plan_id = Column(String, nullable=True)
    tooling_requirements = Column(JSON().with_variant(JSONB, "postgresql"))
    work_instructions = Column(Text, nullable=True)
    document_ids = Column(JSON().with_variant(JSONB, "postgresql"))
    labor_cost_rate = Column(Float, nullable=True)
    overhead_rate = Column(Float, nullable=True)
    properties = Column(JSON().with_variant(JSONB, "postgresql"))

    routing = relationship("Routing", back_populates="operations")


class WorkCenter(Base):
    __tablename__ = "meta_workcenters"

    id = Column(String, primary_key=True)
    code = Column(String(120), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    plant_code = Column(String(120), nullable=True)
    department_code = Column(String(120), nullable=True)
    capacity_per_day = Column(Float, default=8.0)
    efficiency = Column(Float, default=1.0)
    utilization = Column(Float, default=0.9)
    machine_count = Column(Integer, default=1)
    worker_count = Column(Integer, default=1)
    cost_center = Column(String(120), nullable=True)
    labor_rate = Column(Float, nullable=True)
    overhead_rate = Column(Float, nullable=True)
    scheduling_type = Column(String(50), default="finite")
    queue_time_default = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
