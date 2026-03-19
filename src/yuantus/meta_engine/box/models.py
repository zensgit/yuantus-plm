"""
PLM box / packaging domain models.

Mirrors Odoo 18 ``product.packaging`` concepts:
  - BoxItem     (meta_box_items)     – packaging template with dimensions & weight
  - BoxContent  (meta_box_contents)  – items packed inside a box instance
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


class BoxType(str, enum.Enum):
    BOX = "box"
    CARTON = "carton"
    PALLET = "pallet"
    CRATE = "crate"
    ENVELOPE = "envelope"


class BoxState(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BoxItem(Base):
    """Packaging template with dimensions, weight and material info.

    Equivalent to Odoo ``product.packaging``.
    """

    __tablename__ = "meta_box_items"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Classification
    box_type = Column(String(30), default=BoxType.BOX.value, nullable=False)
    state = Column(String(30), default=BoxState.DRAFT.value, nullable=False)

    # Dimensions
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)
    dimension_unit = Column(String(20), default="mm", nullable=False)

    # Weight
    tare_weight = Column(Float, nullable=True)
    max_gross_weight = Column(Float, nullable=True)
    weight_unit = Column(String(20), default="kg", nullable=False)

    # Material & capacity
    material = Column(String(200), nullable=True)
    barcode = Column(String(200), nullable=True)
    max_quantity = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)

    # Product link
    product_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    contents = relationship(
        "BoxContent", back_populates="box", cascade="all, delete-orphan"
    )


class BoxContent(Base):
    """An item packed inside a box instance."""

    __tablename__ = "meta_box_contents"

    id = Column(String, primary_key=True)
    box_id = Column(
        String,
        ForeignKey("meta_box_items.id"),
        nullable=False,
        index=True,
    )
    item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)

    quantity = Column(Float, default=1.0, nullable=False)
    lot_serial = Column(String(200), nullable=True)
    note = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    box = relationship("BoxItem", back_populates="contents")
