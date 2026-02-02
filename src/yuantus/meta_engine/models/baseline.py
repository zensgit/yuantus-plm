from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from yuantus.models.base import Base


class BaselineType(str, enum.Enum):
    DESIGN = "design"
    FUNCTIONAL = "functional"
    PRODUCT = "product"
    RELEASE = "release"
    MANUFACTURING = "manufacturing"


class BaselineScope(str, enum.Enum):
    PRODUCT = "product"
    ASSEMBLY = "assembly"
    ITEM = "item"
    DOCUMENT = "document"


class Baseline(Base):
    """
    Baseline snapshot for BOM/Configuration.
    Stores a frozen BOM tree and metadata for traceability.
    """

    __tablename__ = "meta_baselines"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    baseline_type = Column(String(50), nullable=False, default="bom")
    baseline_number = Column(String(60), nullable=True, unique=True)
    scope = Column(String(50), nullable=True, default=BaselineScope.PRODUCT.value)

    root_item_id = Column(
        String, ForeignKey("meta_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    root_version_id = Column(
        String,
        ForeignKey("meta_item_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    root_config_id = Column(String, nullable=True, index=True)
    eco_id = Column(String, ForeignKey("meta_items.id", ondelete="SET NULL"), nullable=True)

    snapshot = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)

    max_levels = Column(Integer, default=10)
    effective_at = Column(DateTime, nullable=True)
    include_bom = Column(Boolean, default=True)
    include_substitutes = Column(Boolean, default=False)
    include_effectivity = Column(Boolean, default=False)
    include_documents = Column(Boolean, default=True)
    include_relationships = Column(Boolean, default=True)
    line_key = Column(String(50), default="child_config")

    item_count = Column(Integer, default=0)
    relationship_count = Column(Integer, default=0)

    state = Column(String(50), default="draft")
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    validated_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    is_locked = Column(Boolean, default=False)
    locked_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    released_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    members = relationship("BaselineMember", back_populates="baseline", cascade="all, delete-orphan")

    @property
    def effective_date(self) -> datetime | None:
        return self.effective_at

    @effective_date.setter
    def effective_date(self, value: datetime | None) -> None:
        self.effective_at = value

    @property
    def bom_levels(self) -> int | None:
        return self.max_levels

    @bom_levels.setter
    def bom_levels(self, value: int | None) -> None:
        if value is not None:
            self.max_levels = value


class BaselineMember(Base):
    __tablename__ = "meta_baseline_members"

    id = Column(String, primary_key=True)
    baseline_id = Column(String, ForeignKey("meta_baselines.id", ondelete="CASCADE"), nullable=False, index=True)

    item_id = Column(String, ForeignKey("meta_items.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(String, ForeignKey("meta_files.id", ondelete="SET NULL"), nullable=True, index=True)
    relationship_id = Column(String, nullable=True, index=True)

    item_number = Column(String)
    item_revision = Column(String)
    item_generation = Column(Integer)
    item_type = Column(String)

    level = Column(Integer, default=0)
    path = Column(String)
    quantity = Column(String, nullable=True)

    member_type = Column(String, default="item")
    item_state = Column(String)

    baseline = relationship("Baseline", back_populates="members")


class BaselineComparison(Base):
    __tablename__ = "meta_baseline_comparisons"

    id = Column(String, primary_key=True)

    baseline_a_id = Column(String, ForeignKey("meta_baselines.id", ondelete="CASCADE"), nullable=False)
    baseline_b_id = Column(String, ForeignKey("meta_baselines.id", ondelete="CASCADE"), nullable=False)

    added_count = Column(Integer, default=0)
    removed_count = Column(Integer, default=0)
    changed_count = Column(Integer, default=0)
    unchanged_count = Column(Integer, default=0)

    differences = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    compared_at = Column(DateTime, default=datetime.utcnow)
    compared_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
