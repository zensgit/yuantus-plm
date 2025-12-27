from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


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

    snapshot = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)

    max_levels = Column(Integer, default=10)
    effective_at = Column(DateTime, nullable=True)
    include_substitutes = Column(Boolean, default=False)
    include_effectivity = Column(Boolean, default=False)
    line_key = Column(String(50), default="child_config")

    item_count = Column(Integer, default=0)
    relationship_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
