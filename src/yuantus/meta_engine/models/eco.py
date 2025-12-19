"""
ECO (Engineering Change Order) Models
Sprint 3: Complete ECO Change Management System

Architecture Note:
- meta_engine uses "Relationship as Item" pattern
- BOM is NOT a separate table, but Item relationships in meta_items
- source_id → parent item, related_id → child item
- item_type_id = "Part BOM" (relationship type)
- properties stores qty, uom, etc.

Models:
- ECOStage: Change stage definition
- ECO: Engineering Change Order
- ECOApproval: Approval records
- ECOBOMChange: BOM change tracking (references meta_items relationships)
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    Float,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


class ECOType(str, Enum):
    """ECO types"""

    BOM = "bom"
    PRODUCT = "product"
    DOCUMENT = "document"


class ECOState(str, Enum):
    """ECO lifecycle states"""

    DRAFT = "draft"
    PROGRESS = "progress"
    CONFLICT = "conflict"
    APPROVED = "approved"
    DONE = "done"
    CANCELED = "canceled"


class ApprovalType(str, Enum):
    """Approval types for stages"""

    NONE = "none"
    OPTIONAL = "optional"
    MANDATORY = "mandatory"
    COMMENT = "comment"


class ApprovalStatus(str, Enum):
    """Approval status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMENTED = "commented"


class BOMChangeType(str, Enum):
    """BOM change types"""

    ADD = "add"
    REMOVE = "remove"
    UPDATE = "update"


class ECOPriority(str, Enum):
    """ECO priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ECOStage(Base):
    """
    ECO Stage Definition.
    Defines the stages an ECO passes through.
    """

    __tablename__ = "meta_eco_stages"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    sequence = Column(Integer, default=10)
    fold = Column(Boolean, default=False)  # Collapse in Kanban
    is_blocking = Column(Boolean, default=False)

    # Approval configuration
    approval_type = Column(String(20), default="none")  # none/optional/mandatory
    approval_roles = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )  # List of roles that can approve
    min_approvals = Column(Integer, default=1)  # Minimum approvals needed

    auto_progress = Column(Boolean, default=False)  # Auto-move when approved
    description = Column(Text, nullable=True)

    company_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ecos = relationship("ECO", back_populates="stage")
    approvals = relationship("ECOApproval", back_populates="stage")


class ECO(Base):
    """
    Engineering Change Order.
    Main ECO record tracking changes to products/BOMs.

    Architecture:
    - product_id: references meta_items.id (String UUID) - the product being changed
    - In meta_engine, BOM is represented as Item relationships (source_id → related_id)
    - ECOBOMChange tracks changes to these relationship Items
    """

    __tablename__ = "meta_ecos"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    eco_type = Column(String(20), nullable=False, default="bom")

    # Related product (meta_items.id - String UUID)
    product_id = Column(
        String,
        ForeignKey("meta_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Version tracking for the product
    # source_version_id: The version being modified
    # target_version_id: The new version being created
    source_version_id = Column(
        String, ForeignKey("meta_item_versions.id", ondelete="SET NULL"), nullable=True
    )
    target_version_id = Column(
        String, ForeignKey("meta_item_versions.id", ondelete="SET NULL"), nullable=True
    )

    # Stage and state
    stage_id = Column(
        String, ForeignKey("meta_eco_stages.id"), nullable=True, index=True
    )
    state = Column(String(20), default="draft", index=True)
    current_state = Column(
        String, ForeignKey("meta_lifecycle_states.id"), nullable=True
    )  # For LifecycleService

    @property
    def item_type_id(self):
        return "ECO"

    kanban_state = Column(String(20), default="normal")  # normal/blocked/done

    # Approval
    approval_deadline = Column(DateTime, nullable=True)

    # Version tracking (for display)
    product_version_before = Column(String(20), nullable=True)
    product_version_after = Column(String(20), nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    priority = Column(String(10), default="normal")
    effectivity_date = Column(DateTime, nullable=True)

    # Audit
    created_by_id = Column(
        Integer, ForeignKey("rbac_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    company_id = Column(String, nullable=True)

    # Relationships
    stage = relationship("ECOStage", back_populates="ecos")
    product = relationship(
        "yuantus.meta_engine.models.item.Item", foreign_keys=[product_id]
    )
    source_version = relationship(
        "yuantus.meta_engine.version.models.ItemVersion",
        foreign_keys=[source_version_id],
    )
    target_version = relationship(
        "yuantus.meta_engine.version.models.ItemVersion",
        foreign_keys=[target_version_id],
    )
    created_by = relationship("yuantus.security.rbac.models.RBACUser")

    approvals = relationship(
        "ECOApproval",
        back_populates="eco",
        cascade="all, delete-orphan",
        order_by="ECOApproval.created_at",
    )

    bom_changes = relationship(
        "ECOBOMChange",
        back_populates="eco",
        cascade="all, delete-orphan",
        order_by="ECOBOMChange.created_at",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "eco_type": self.eco_type,
            "product_id": self.product_id,
            "source_version_id": self.source_version_id,
            "target_version_id": self.target_version_id,
            "stage_id": self.stage_id,
            "state": self.state,
            "kanban_state": self.kanban_state,
            "priority": self.priority,
            "description": self.description,
            "product_version_before": self.product_version_before,
            "product_version_after": self.product_version_after,
            "effectivity_date": (
                self.effectivity_date.isoformat() if self.effectivity_date else None
            ),
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ECOApproval(Base):
    """
    ECO Approval Record.
    Tracks approval votes for each stage.
    """

    __tablename__ = "meta_eco_approvals"

    id = Column(String, primary_key=True)
    eco_id = Column(
        String,
        ForeignKey("meta_ecos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_id = Column(String, ForeignKey("meta_eco_stages.id"), nullable=False)

    # Approval configuration
    approval_type = Column(String(20), default="mandatory")
    required_role = Column(String(100), nullable=True)

    # Result
    user_id = Column(
        Integer, ForeignKey("rbac_users.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(String(20), default="pending", index=True)
    comment = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    eco = relationship("ECO", back_populates="approvals")
    stage = relationship("ECOStage", back_populates="approvals")
    user = relationship("yuantus.security.rbac.models.RBACUser")

    def to_dict(self):
        return {
            "id": self.id,
            "eco_id": self.eco_id,
            "stage_id": self.stage_id,
            "approval_type": self.approval_type,
            "required_role": self.required_role,
            "user_id": self.user_id,
            "status": self.status,
            "comment": self.comment,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ECOBOMChange(Base):
    """
    ECO BOM Change Record.
    Tracks individual changes to BOM lines.

    Architecture Note:
    In meta_engine, BOM is represented as relationship Items:
    - relationship_item_id: The meta_items.id of the BOM relationship row
    - parent_item_id: The parent part (source_id in meta_items)
    - child_item_id: The child part (related_id in meta_items)

    The relationship Item stores qty, uom etc in its properties JSONB.
    """

    __tablename__ = "meta_eco_bom_changes"

    id = Column(String, primary_key=True)
    eco_id = Column(
        String,
        ForeignKey("meta_ecos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Change type
    change_type = Column(String(20), nullable=False, index=True)

    # BOM relationship info (all reference meta_items.id)
    # The relationship Item itself (item_type = "Part BOM" or similar)
    relationship_item_id = Column(
        String, ForeignKey("meta_items.id", ondelete="SET NULL"), nullable=True
    )
    # Parent part in the BOM
    parent_item_id = Column(
        String, ForeignKey("meta_items.id", ondelete="SET NULL"), nullable=True
    )
    # Child part in the BOM
    child_item_id = Column(
        String, ForeignKey("meta_items.id", ondelete="SET NULL"), nullable=True
    )

    # Old values (from relationship Item properties)
    old_qty = Column(Float, nullable=True)
    old_uom = Column(String(50), nullable=True)
    old_sequence = Column(Integer, nullable=True)
    old_properties = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )  # Full old properties snapshot

    # New values
    new_qty = Column(Float, nullable=True)
    new_uom = Column(String(50), nullable=True)
    new_sequence = Column(Integer, nullable=True)
    new_properties = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )  # Full new properties snapshot

    # Conflict tracking (Rebase)
    conflict = Column(Boolean, default=False)
    conflict_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    eco = relationship("ECO", back_populates="bom_changes")
    relationship_item = relationship(
        "yuantus.meta_engine.models.item.Item", foreign_keys=[relationship_item_id]
    )
    parent_item = relationship(
        "yuantus.meta_engine.models.item.Item", foreign_keys=[parent_item_id]
    )
    child_item = relationship(
        "yuantus.meta_engine.models.item.Item", foreign_keys=[child_item_id]
    )

    # Indexes
    __table_args__ = (
        Index("ix_eco_bom_change_parent", "parent_item_id"),
        Index("ix_eco_bom_change_child", "child_item_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "eco_id": self.eco_id,
            "change_type": self.change_type,
            "relationship_item_id": self.relationship_item_id,
            "parent_item_id": self.parent_item_id,
            "child_item_id": self.child_item_id,
            "old_qty": self.old_qty,
            "new_qty": self.new_qty,
            "old_uom": self.old_uom,
            "new_uom": self.new_uom,
            "old_properties": self.old_properties,
            "new_properties": self.new_properties,
            "conflict": self.conflict,
            "conflict_reason": self.conflict_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
