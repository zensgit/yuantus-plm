"""Governed BOM multi-table write-back (PLM-COLLAB Phase-7, design-lock #901 + G1-G5).

Provider-side write path behind the ``bom_multitable_writeback`` entitlement. Applies a
whitelisted, lifecycle-guarded edit to ONE ``Part BOM`` line with provider-side single-use
idempotency/replay + an atomic audit row (one ``meta_bom_writeback_audit`` insert serves
guard + audit + replay cache). Mirrors the engine UPDATE op (copy-on-write ``properties``
reassign) and the ``MesConsumptionInbox`` idempotency idiom (``begin_nested`` + IntegrityError).

Guard responsibilities here (the router owns 403/403/400 BEFORE calling this): 404 (line in
part) -> 409 (parent lifecycle-lock) -> idempotency -> mutate.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.models.bom_writeback_audit import BomWritebackAudit
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType

# G2: the WRITE entitlement key lives in the WRITE module, NOT the read projection service.
WRITE_FEATURE_KEY = "bom_multitable_writeback"
BOM_LINE_TYPE = "Part BOM"

# The ONLY line cells this governed write accepts. Unknown keys are dropped; an all-unknown
# body canonicalizes to empty -> 400, so "empty whitelist" is a real fail-closed boundary.
WRITE_WHITELIST = ("quantity", "uom", "find_num", "refdes")


class WritebackError(Exception):
    """Service-level error carrying an HTTP status + detail for the router to surface."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def canonical_patch(raw: Any) -> Dict[str, Any]:
    """Whitelist-filter + null-clear -> the canonical patch this write applies.

    - only ``WRITE_WHITELIST`` keys survive (unknown keys dropped -- they never reach the DB);
    - an explicit ``null`` is KEPT as ``None`` (a real "clear this cell" mutation);
    - raises ``WritebackError(400)`` if the body is not a JSON object or canonicalizes to
      empty (the empty-whitelist fail-closed boundary).

    The canonical form (not raw JSON) is what gets fingerprinted, so int/float, unknown
    fields, and key order can never cause a false (or missed) same-key conflict.
    """
    if not isinstance(raw, dict):
        raise WritebackError(400, "body must be a JSON object")
    patch: Dict[str, Any] = {}
    for key in WRITE_WHITELIST:
        if key in raw:
            patch[key] = raw[key]
    if not patch:
        raise WritebackError(400, "no editable BOM-line fields in request (empty whitelist)")
    return patch


def request_fingerprint(patch: Dict[str, Any]) -> str:
    """sha256 of the CANONICAL patch (sorted keys) -- same key + different payload -> 409."""
    blob = json.dumps(patch, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class BomMultitableWritebackService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def apply(
        self,
        *,
        part_id: str,
        bom_line_id: str,
        idempotency_key: str,
        patch: Dict[str, Any],
        actor_user_id: str,
        tenant_id: Optional[str],
        org_id: Optional[str],
    ) -> Dict[str, Any]:
        """404 (part/line) -> 409 (parent lifecycle) -> idempotency -> mutate.

        Returns the 200 body dict ``{ok, bom_line_id}`` (a true replay also returns
        ``replayed=True``). Raises ``WritebackError`` for 400/404/409. The CALLER commits on
        success and rolls back on error -- so the audit row and the mutation are atomic
        (audit-insert failure -> no mutation; mutation failure -> caller rollback drops the
        audit row too).
        """
        # 404: the parent Part must exist (and be a Part)...
        part = self.session.get(Item, part_id)
        if part is None or part.item_type_id != "Part":
            raise WritebackError(404, "Part not found")
        # ...and the line must exist AND belong to THIS part (line in part: a "Part BOM"
        # relationship whose source_id is the part).
        line = self.session.get(Item, bom_line_id)
        if (
            line is None
            or line.item_type_id != BOM_LINE_TYPE
            or line.source_id != part_id
        ):
            raise WritebackError(404, "BOM line not found on this part")

        # 409: a Released/locked PARENT BOM is not editable here (revising it is the deferred
        # ECO route). Reuses the add_bom_child precedent (is_item_locked -> 409).
        part_type = self.session.get(ItemType, part.item_type_id)
        locked, locked_state = is_item_locked(self.session, part, part_type)
        if locked:
            raise WritebackError(
                409, f"Item is locked in state '{locked_state or part.state}'"
            )

        request_hash = request_fingerprint(patch)
        # before-snapshot of ONLY the touched cells, taken BEFORE any reassignment.
        current = dict(line.properties or {})
        before = {key: current.get(key) for key in patch}
        after = dict(before)
        after.update(patch)

        # G3 / P1-G3: insert the combined audit+idempotency row FIRST inside a SAVEPOINT, so a
        # duplicate key short-circuits BEFORE any mutation.
        audit = BomWritebackAudit(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            org_id=org_id,
            part_id=part_id,
            bom_line_id=bom_line_id,
            before=before,
            after=after,
            status="applied",
        )
        try:
            with self.session.begin_nested():
                self.session.add(audit)
                self.session.flush()
        except IntegrityError:
            existing = (
                self.session.query(BomWritebackAudit)
                .filter(BomWritebackAudit.idempotency_key == idempotency_key)
                .one_or_none()
            )
            if existing is None:
                raise
            # Same key + DIFFERENT canonical payload -> conflict; never re-apply a stale write.
            if existing.request_hash != request_hash:
                raise WritebackError(
                    409, "Idempotency-Key already used with a different payload"
                )
            # True replay: return the cached result WITHOUT re-applying the mutation (G3).
            return {"ok": True, "bom_line_id": bom_line_id, "replayed": True}

        # Fresh key -> apply via copy-on-write WHOLE-DICT reassign (P1-properties: never
        # line.properties.update(...) in place -- SQLAlchemy JSON dirty-detection is unreliable).
        merged = dict(line.properties or {})
        merged.update(patch)
        line.properties = merged
        line.modified_by_id = int(actor_user_id) if str(actor_user_id).isdigit() else None
        self.session.flush()
        return {"ok": True, "bom_line_id": bom_line_id}
