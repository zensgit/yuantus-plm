"""PLM-COLLAB BOM multi-table routes (P3-A projection + P3-D1 embed-token mint).

``GET /api/v1/bom/multitable/{part_id}/context`` (P3-A) -- a governed READ-ONLY projection of
a part + its FULL (flattened) BOM tree into a review-table context (the consumer side is
P3-C). READ-ONLY: no write-back, no audit.

``POST /api/v1/bom/multitable/{part_id}/embed-token`` (P3-D1) -- mints a short-lived Ed25519
embed token so the BOM review can later be shown INSIDE the PLM UI via an embedded MetaSheet
iframe (the consumer-side verifier + host is P3-D2). This route DOES audit the issuance.

Both share the PINNED gate: authenticate (get_current_user) -> is_entitled("bom_multitable")
-> ONLY THEN query the part -> Part-type guard -> PLM read permission. An unentitled caller
gets a null affordance (``context:null`` / ``embed_token:null``) and the part is NEVER queried,
so object existence is not leaked. The entitlement gate is the single ``is_entitled`` check (no
second license read, no ``license_data`` authorization). ``bom_multitable`` is lit (P3-B) to
its own SKU ``plm.bom_multitable``.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, StrictFloat, StrictInt
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.app_framework.entitlement_service import EntitlementService
from yuantus.meta_engine.app_framework.license_scope import resolve_license_scope
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_multitable_embed_token_service import (
    EmbedTokenNotConfigured,
    is_origin_allowed,
    mint_embed_token,
)
from yuantus.meta_engine.services.bom_multitable_projection_service import (
    BOM_LINE_TYPE,
    FEATURE_KEY,
    BOMMultitableProjectionService,
)
from sqlalchemy.exc import IntegrityError
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.models.bom_writeback_audit import BomWritebackAudit
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.models.audit import AuditLog

bom_multitable_router = APIRouter(prefix="/bom", tags=["BOM"])


class EmbedTokenRequest(BaseModel):
    """The PLM UI requests an embed token for a specific target origin (the iframe host)."""

    origin: str


class BomLineWriteBackRequest(BaseModel):
    """PLM-COLLAB Phase 7 write-back: the whitelisted editable cells of a BOM multi-table line.

    All four are optional and mirror the consumer contract (#3332): only the cells the user
    actually changed are sent; ``null`` is a real "clear this cell" value (preserved); an
    all-empty body is rejected. ``model_fields_set`` distinguishes "sent as null" (a clear)
    from "absent" (untouched), so a null cell is a real edit while an omitted cell is not.
    """

    # number | string | null only -- StrictInt/StrictFloat reject bool, and a list/object
    # is rejected outright, so a non-business value can never reach a governed BOM cell.
    quantity: Optional[Union[StrictInt, StrictFloat, str]] = None
    uom: Optional[str] = None
    find_num: Optional[str] = None
    refdes: Optional[str] = None


# Phase 7 write side: a SEPARATE, write-scoped SKU from the read projection (Fork 2, #884/#899).
WRITE_FEATURE_KEY = "bom_multitable_writeback"
# The editable business cells of a "Part BOM" relationship-Item (projection's _LINE_REL_FIELDS).
_EDITABLE_CELLS = ("quantity", "uom", "find_num", "refdes")


def _affordance(entitled: bool) -> Dict[str, Any]:
    return {
        "feature_key": FEATURE_KEY,
        "entitled": entitled,
        "upgrade": {"available": not entitled},
    }


@bom_multitable_router.get("/multitable/{part_id}/context")
def bom_multitable_context(
    part_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Read-only BOM-context projection. PINNED order: auth -> entitled -> part -> Part-type
    -> permission.

    Unentitled -> ``context: null`` + upgrade affordance, WITHOUT touching the part (no
    existence leak). Entitled but part absent -> 404; a non-Part Item -> 400; read permission
    denied -> 403.
    """
    if not EntitlementService(db).is_entitled(FEATURE_KEY):
        # Do NOT look up the part -- unentitled callers must not learn whether it exists.
        return {**_affordance(False), "context": None}

    root = db.get(Item, part_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Part not found")
    # The endpoint is {part_id} and the projection is a Part BOM review; a non-Part Item is
    # a bad request (mirrors bom_tree_router's `item_type_id != "Part"` 400 guard). Parts
    # (and BOM-line targets) are item_type_id == "Part" throughout the engine.
    if root.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Item is not a Part")

    perm = MetaPermissionService(db)
    user_id = str(user.id)
    if not perm.check_permission(
        root.item_type_id, AMLAction.get, user_id=user_id, user_roles=user.roles
    ) or not perm.check_permission(
        BOM_LINE_TYPE, AMLAction.get, user_id=user_id, user_roles=user.roles
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    context = BOMMultitableProjectionService(db).project_context(part_id)
    return {**_affordance(True), "context": context}


@bom_multitable_router.post("/multitable/{part_id}/embed-token")
def bom_multitable_embed_token(
    part_id: str,
    body: EmbedTokenRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """PLM-COLLAB-P3-D1: mint a short-lived Ed25519 embed token for a Part's BOM review.

    PINNED order (mirrors the GET gate, then mints): auth -> is_entitled -> part -> Part-type
    -> read permission -> [mint configured? else 503 fail-closed] -> origin allowlist (403)
    -> mint + jti audit. Unentitled -> ``embed_token: null`` + upgrade affordance, WITHOUT
    touching the part (no existence leak) and WITHOUT minting. The token authorizes nothing but
    the P3-A read projection; the consumer (P3-D2) verifies it offline with the PUBLIC key.
    """
    if not EntitlementService(db).is_entitled(FEATURE_KEY):
        # Do NOT look up the part -- unentitled callers get no token and learn nothing.
        return {**_affordance(False), "embed_token": None}

    root = db.get(Item, part_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Part not found")
    if root.item_type_id != "Part":
        raise HTTPException(status_code=400, detail="Item is not a Part")

    perm = MetaPermissionService(db)
    user_id = str(user.id)
    if not perm.check_permission(
        root.item_type_id, AMLAction.get, user_id=user_id, user_roles=user.roles
    ) or not perm.check_permission(
        BOM_LINE_TYPE, AMLAction.get, user_id=user_id, user_roles=user.roles
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    settings = get_settings()
    # fail-closed: a deployment without a signing key cannot mint
    if not settings.EMBED_TOKEN_SIGNING_KEY:
        raise HTTPException(status_code=503, detail="embed token minting unavailable")

    origin = (body.origin or "").strip()
    if not is_origin_allowed(origin, settings.EMBED_ALLOWED_ORIGINS):
        raise HTTPException(status_code=403, detail="embed origin not allowed")

    tenant_id, org_id = resolve_license_scope()
    try:
        minted = mint_embed_token(
            user_id=user.id,
            tenant_id=tenant_id,
            org_id=org_id,
            part_id=part_id,
            origin=origin,
            audience=settings.EMBED_TOKEN_AUDIENCE,
            signing_key_b64=settings.EMBED_TOKEN_SIGNING_KEY,
            key_id=settings.EMBED_TOKEN_KEY_ID,
            ttl_seconds=settings.EMBED_TOKEN_TTL_SECONDS,
        )
    except EmbedTokenNotConfigured as exc:
        # unset OR invalid signing key (malformed base64 / wrong-length seed) -> fail closed,
        # never a 500 that leaks the deployment's key state.
        raise HTTPException(status_code=503, detail="embed token minting unavailable") from exc

    # jti-trackable audit of the issuance; NEVER record the token itself.
    db.add(
        AuditLog(
            method="MINT",
            path=f"/api/v1/bom/multitable/{part_id}/embed-token?jti={minted['jti']}",
            status_code=200,
            duration_ms=0,
            user_id=int(user.id),
            tenant_id=tenant_id,
            org_id=org_id,
        )
    )
    db.commit()

    return {
        **_affordance(True),
        "embed_token": minted["token"],
        "token_type": "embed",
        "expires_in": minted["expires_in"],
        "jti": minted["jti"],
        "aud": minted["aud"],
        "embed_origin": origin,
    }


@bom_multitable_router.patch("/multitable/{part_id}/lines/{bom_line_id}")
def bom_multitable_writeback(
    part_id: str,
    bom_line_id: str,
    body: BomLineWriteBackRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """PLM-COLLAB-P7: governed write-back of a single BOM multi-table line (ratified #901).

    Satisfies the consumer contract (metasheet2 #3332): synchronous
    ``PATCH .../lines/{bom_line_id}`` with a whitelist body ``{quantity?, uom?, find_num?, refdes?}``
    plus an ``Idempotency-Key`` header -> ``200 {ok, bom_line_id}``.

    This is the Draft/editable-state FAST PATH: it applies the cell edit IN PLACE
    (last-write-wins), guarded by a lifecycle lock; it is NOT a pending-ECO intent (the #896 draft
    is superseded) and the ECO route for revising Released/locked BOMs is a deferred capability.

    Guard order (write-precedent 403s; fail-closed before any object lookup):
    ``is_entitled("bom_multitable_writeback")`` 403 -> "Part BOM"/update permission 403 ->
    empty-whitelist|missing-Idempotency-Key 400 -> part-missing|line-not-a-direct-"Part BOM"-child
    404 -> parent lifecycle-locked 409 (``is_item_locked``) -> apply. Apply is atomic: ONE
    ``meta_bom_writeback_audit`` row (unique ``idempotency_key``) is BOTH the single-use replay
    guard AND the before/after audit -- a duplicate key with the SAME payload returns the cached
    200 without re-applying, a duplicate key with a DIFFERENT payload is a 409, and an audit-insert
    failure rolls the property mutation back. Cross-tenant safety is the standard tenant-scoped
    data access (the embed token is consumer-internal, not on this provider wire, #899 1).
    """
    # 1. WRITE entitlement -- 403 first (no existence-leak on a write surface).
    if not EntitlementService(db).is_entitled(WRITE_FEATURE_KEY):
        raise HTTPException(status_code=403, detail="bom_multitable_writeback not entitled")

    # 2. WRITE permission on the BOM-line type (Fork 2: "Part BOM" / update).
    perm = MetaPermissionService(db)
    if not perm.check_permission(
        BOM_LINE_TYPE, AMLAction.update, user_id=str(user.id), user_roles=user.roles
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    # 3. fail-fast 400 BEFORE any object lookup: empty whitelist OR missing Idempotency-Key.
    requested = {c: getattr(body, c) for c in _EDITABLE_CELLS if c in body.model_fields_set}
    if not requested:
        raise HTTPException(
            status_code=400,
            detail="empty patch: at least one of quantity, uom, find_num, refdes is required",
        )
    key = (idempotency_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="missing required Idempotency-Key header")

    # 4. 404: the part, then the line must be a "Part BOM" that is a DIRECT child of part_id.
    part = db.get(Item, part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="Part not found")
    line = db.get(Item, bom_line_id)
    if line is None or line.item_type_id != BOM_LINE_TYPE or line.source_id != part_id:
        raise HTTPException(status_code=404, detail="BOM line not found under part")

    # 5. 409: the parent assembly must not be lifecycle-locked (the add_bom_child precedent).
    part_type = db.get(ItemType, part.item_type_id)
    locked, locked_state = is_item_locked(db, part, part_type)
    if locked:
        raise HTTPException(
            status_code=409, detail=f"Item is locked in state '{locked_state or part.state}'"
        )

    # 6. apply: before/after snapshot (BEFORE mutation), then ONE audit+replay row + the in-place
    #    property mutation, committed atomically.
    line_props = dict(line.properties or {})
    before = {c: line_props.get(c) for c in _EDITABLE_CELLS}
    after = {**before, **requested}
    tenant_id, org_id = resolve_license_scope()

    audit = BomWritebackAudit(
        idempotency_key=key,
        user_id=int(user.id),
        tenant_id=tenant_id,
        org_id=org_id,
        part_id=part_id,
        bom_line_id=bom_line_id,
        before=before,
        after=after,
        status="applied",
    )
    # G3: the audit/replay row goes in BEFORE the mutation, in one transaction (the proven
    # consumption_mes_inbox_service pattern). A replayed key collides on the UNIQUE
    # idempotency_key at the nested flush -> the savepoint rolls back and we return the cached
    # result (or 409) WITHOUT mutating; ONLY a fresh key proceeds to apply the cell edit. `before`
    # was snapshotted above, before any reassignment.
    try:
        with db.begin_nested():
            db.add(audit)
            db.flush()
    except IntegrityError:
        existing = db.query(BomWritebackAudit).filter_by(idempotency_key=key).one_or_none()
        if existing is None:
            raise
        if existing.bom_line_id != bom_line_id or (existing.after or {}) != after:
            # same key but a DIFFERENT line or payload -> conflict. An Idempotency-Key identifies
            # exactly one (line, payload); never silently serve one line's result for another.
            raise HTTPException(
                status_code=409,
                detail="Idempotency-Key reused for a different line or payload",
            )
        # same key, same line, same payload -> cached success, never mutated.
        return {"ok": True, "bom_line_id": existing.bom_line_id}

    # fresh key: apply the cell edit in place; the fresh audit row + the mutation commit together,
    # and a commit failure rolls BOTH back (no partial state -- a governed write never persists
    # without its diff, #901 3).
    line.properties = {**line_props, **requested}
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"ok": True, "bom_line_id": bom_line_id}
