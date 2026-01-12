"""
Plugin Configuration Models
Stores per-tenant/org plugin configuration payloads.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


class PluginConfig(Base):
    __tablename__ = "meta_plugin_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    plugin_id = Column(String(120), nullable=False, index=True)
    tenant_id = Column(String(120), nullable=False, default="default", index=True)
    org_id = Column(String(120), nullable=False, default="default", index=True)

    config = Column(JSON().with_variant(JSONB, "postgresql"), default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "plugin_id", "tenant_id", "org_id", name="uq_plugin_config_scope"
        ),
    )
