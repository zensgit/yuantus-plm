"""PLM-COLLAB Phase 7 — governed BOM multi-table write-back audit + single-use replay cache.

Per the ratified Day-2 design (#901 §2/§3), ONE ``meta_bom_writeback_audit`` row serves BOTH the
domain audit AND the idempotency/replay cache (a single insert):

- ``idempotency_key`` is UNIQUE -> a retried relay (same key) collides on insert and returns the
  cached ``{ok, bom_line_id}`` WITHOUT re-applying; a same-key/different-payload retry is a 409.
- ``before`` / ``after`` are the touched-cell JSON snapshots (the governed change diff), captured
  BEFORE the property reassignment and committed ATOMICALLY with the mutation -- an audit-insert
  failure rolls the property mutation back (a governed write must not succeed without its diff).

The global ``AuditLogMiddleware`` still records the HTTP row separately; this is the domain record.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


class BomWritebackAudit(Base):
    __tablename__ = "meta_bom_writeback_audit"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # explicit per-edit Idempotency-Key (consumer-supplied); UNIQUE = single-use/replay guard
    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    tenant_id = Column(String(64), nullable=True, index=True)
    org_id = Column(String(64), nullable=True, index=True)
    part_id = Column(String, nullable=False, index=True)
    bom_line_id = Column(String, nullable=False, index=True)
    before = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    after = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    status = Column(String(16), nullable=False, default="applied")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
