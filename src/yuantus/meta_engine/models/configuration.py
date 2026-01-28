from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from yuantus.models.base import Base


class ConfigOptionSet(Base):
    """Configuration option sets for variant rules."""

    __tablename__ = "meta_config_option_sets"

    id = Column(String, primary_key=True)
    name = Column(String(120), unique=True, index=True, nullable=False)
    label = Column(String(200), nullable=True)
    description = Column(String, nullable=True)
    item_type_id = Column(
        String, ForeignKey("meta_item_types.id"), nullable=True, index=True
    )
    is_active = Column(Boolean, default=True)
    config = Column(JSON().with_variant(JSONB, "postgresql"), default=dict)
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
    sort_order = Column(Integer, default=0)
    is_default = Column(Boolean, default=False)
    extra = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
