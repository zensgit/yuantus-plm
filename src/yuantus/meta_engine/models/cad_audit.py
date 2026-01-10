from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


class CadChangeLog(Base):
    __tablename__ = "cad_change_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, index=True, nullable=False)
    action = Column(String, nullable=False)
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    tenant_id = Column(String(64), nullable=True, index=True)
    org_id = Column(String(64), nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
