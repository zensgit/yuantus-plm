import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from yuantus.models.base import Base


class OptionValueType(str, enum.Enum):
    """Configuration option value types."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ITEM_REF = "item_ref"


class ConfigOptionSet(Base):
    """Configuration option sets for variant rules."""

    __tablename__ = "meta_config_option_sets"

    id = Column(String, primary_key=True)
    name = Column(String(120), unique=True, index=True, nullable=False)
    label = Column(String(200), nullable=True)
    description = Column(String, nullable=True)
    value_type = Column(String(50), default=OptionValueType.STRING.value)
    allow_multiple = Column(Boolean, default=False)
    is_required = Column(Boolean, default=False)
    default_value = Column(String(200), nullable=True)
    sequence = Column(Integer, default=0)
    item_type_id = Column(
        String, ForeignKey("meta_item_types.id"), nullable=True, index=True
    )
    is_active = Column(Boolean, default=True)
    config = Column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    options = relationship(
        "ConfigOption",
        backref="option_set",
        cascade="all, delete-orphan",
        order_by="ConfigOption.sort_order",
    )


class ConfigOption(Base):
    """Individual selectable options within a set."""

    __tablename__ = "meta_config_options"
    __table_args__ = (
        UniqueConstraint("option_set_id", "key", name="uq_config_option_key"),
    )

    id = Column(String, primary_key=True)
    option_set_id = Column(
        String, ForeignKey("meta_config_option_sets.id", ondelete="CASCADE"), index=True
    )
    key = Column(String(120), nullable=False)
    label = Column(String(200), nullable=True)
    value = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    ref_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    extra = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VariantRule(Base):
    """Variant rules for configuration-driven BOM adjustments."""

    __tablename__ = "meta_variant_rules"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    parent_item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True, index=True)
    parent_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True, index=True)
    condition = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    action_type = Column(String(50), nullable=False)  # include|exclude|substitute|modify_qty
    target_item_id = Column(String, ForeignKey("meta_items.id"), nullable=True)
    target_relationship_id = Column(String, ForeignKey("meta_items.id"), nullable=True)
    action_params = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)


class ProductConfiguration(Base):
    """Saved configuration selections for a product."""

    __tablename__ = "meta_product_configurations"

    id = Column(String, primary_key=True)
    product_item_id = Column(String, ForeignKey("meta_items.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    selections = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    effective_bom_cache = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    cache_updated_at = Column(DateTime(timezone=True), nullable=True)
    state = Column(String(50), default="draft")
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
