import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from yuantus.models.base import Base


class Effectivity(Base):
    """
    Effectivity Scope for Items or Relationships.
    ADR-005 Implementation.

    Supports multiple effectivity types:
    - Date: Based on date range (v1.2 MVP)
    - Lot: Based on lot number range (v1.4+)
    - Serial: Based on serial numbers (v1.4+)
    - Unit: Based on unit positions (v2.0+)
    """

    __tablename__ = "meta_effectivities"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))

    # The object being controlled (usually a Relationship Item or an Item Version)
    item_id = Column(
        String,
        ForeignKey("meta_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Deprecated, use version_id",
    )
    version_id = Column(
        String,
        ForeignKey("meta_item_versions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    version = relationship(
        "yuantus.meta_engine.version.models.ItemVersion", backref="effectivities"
    )

    # Type: "Date", "Lot", "Serial", "Unit"
    effectivity_type = Column(
        String(32),
        default="Date",
        nullable=False,
        index=True,
        comment="Type: Date, Lot, Serial, Unit",
    )

    # Date Range (v1.2 MVP)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Extension payload for future effectivity types (v1.4+)
    # Lot: {"lot_start": "L001", "lot_end": "L999"}
    # Serial: {"serials": ["SN001", "SN002", "SN003"]}
    # Unit: {"unit_positions": ["LEFT-WING-1", "LEFT-WING-2"]}
    payload = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        default=dict,
        comment="Extension data for Lot/Serial/Unit effectivity",
    )

    # Audit fields
    created_at = Column(DateTime, server_default="now()")
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
