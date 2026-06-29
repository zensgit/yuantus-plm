"""Phase-7 BOM multi-table write-back audit + idempotency/replay row (T9-W governed write).

ONE row serves BOTH the write audit AND the single-use idempotency/replay cache
(design-lock #901 §2/§3): a UNIQUE ``idempotency_key`` makes a replay one row;
``request_hash`` (a canonical-payload fingerprint -- whitelist-filtered + null-clear,
NOT raw JSON) distinguishes a same-key/different-payload conflict (409) from a true replay
(cached 200); ``before``/``after`` capture the touched-cell diff. The row is committed
atomically with the property mutation -- an audit-insert failure rolls back the write
(a governed write must not succeed without its diff). Mirrors the proven
``MesConsumptionInbox`` idempotency model (UNIQUE ``idempotency_key`` + ``begin_nested``).
"""
from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _json() -> JSON:
    return JSON().with_variant(JSONB, "postgresql")


class BomWritebackAudit(Base):
    """``meta_bom_writeback_audit`` -- guard + audit + cached-replay, one insert per write."""

    __tablename__ = "meta_bom_writeback_audit"

    id = Column(String, primary_key=True, default=_uuid)
    # Consumer-supplied per-edit ``Idempotency-Key`` (G2/G3); UNIQUE so a replay is one row.
    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)
    # sha256 of the CANONICAL patch (whitelist-filtered + null-clear semantics) so a replay
    # with the SAME key but a DIFFERENT payload is a 409 conflict, not a silent cached 200.
    request_hash = Column(String(64), nullable=False)
    actor_user_id = Column(String, nullable=True)
    tenant_id = Column(String, nullable=True, index=True)
    org_id = Column(String, nullable=True)
    part_id = Column(String, nullable=False, index=True)
    bom_line_id = Column(String, nullable=False, index=True)
    # touched-cells before/after the mutation (snapshotted BEFORE properties reassignment).
    before = Column(_json(), nullable=True)
    after = Column(_json(), nullable=True)
    status = Column(String(20), nullable=False, default="applied")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
