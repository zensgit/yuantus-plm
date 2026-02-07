from __future__ import annotations

import csv
from datetime import datetime
import io
import json
from typing import Any, Dict, List, Optional
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.eco_service import ECOService
from yuantus.meta_engine.services.impact_analysis_service import (
    CurrentUserView,
    ImpactAnalysisService,
)
from yuantus.meta_engine.services.release_readiness_service import ReleaseReadinessService
from yuantus.meta_engine.web.impact_router import (
    BaselinesSummary,
    ESignSummary,
    ImpactSummaryResponse,
    WhereUsedSummary,
)
from yuantus.meta_engine.web.release_readiness_router import (
    ReleaseReadinessResponse,
    _build_response,
)


item_cockpit_router = APIRouter(prefix="/items", tags=["Item Cockpit"])


def _ensure_admin(user: CurrentUser) -> None:
    roles = {str(r).lower() for r in (user.roles or [])}
    if bool(getattr(user, "is_superuser", False)):
        return
    if "admin" in roles or "superuser" in roles:
        return
    raise HTTPException(status_code=403, detail="Admin permission required")


class CockpitItem(BaseModel):
    id: str
    item_type_id: str
    config_id: str
    generation: int
    state: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class OpenEcoHit(BaseModel):
    id: str
    name: str
    state: Optional[str] = None
    stage_id: Optional[str] = None
    priority: Optional[str] = None
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class OpenEcosSummary(BaseModel):
    total: int
    hits: List[OpenEcoHit] = Field(default_factory=list)


class CockpitLinks(BaseModel):
    impact_export: str
    release_readiness_export: str


class ItemCockpitResponse(BaseModel):
    item: CockpitItem
    generated_at: datetime
    impact_summary: ImpactSummaryResponse
    release_readiness: ReleaseReadinessResponse
    open_ecos: OpenEcosSummary
    links: CockpitLinks


def _csv_bytes(*, rows: List[Dict[str, Any]], columns: List[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(list(columns))
    for row in rows:
        out_row: List[str] = []
        for col in columns:
            value = (row or {}).get(col)
            if isinstance(value, (dict, list)):
                out_row.append(json.dumps(value, ensure_ascii=False, default=str))
            elif value is None:
                out_row.append("")
            else:
                out_row.append(str(value))
        writer.writerow(out_row)
    return buffer.getvalue().encode("utf-8-sig")


def _zip_bytes(*, files: Dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content or b"")
    return buffer.getvalue()


def _serialize_item_subset(item: Item) -> CockpitItem:
    props = item.properties or {}
    subset = {
        "item_number": props.get("item_number") or props.get("number"),
        "name": props.get("name"),
        "revision": props.get("revision"),
    }
    return CockpitItem(
        id=str(item.id),
        item_type_id=str(item.item_type_id),
        config_id=str(item.config_id),
        generation=int(item.generation or 0),
        state=item.state,
        properties=subset,
    )


def _build_cockpit(
    *,
    item_id: str,
    ruleset_id: str,
    where_used_recursive: bool,
    where_used_max_levels: int,
    where_used_limit: int,
    baseline_limit: int,
    signature_limit: int,
    mbom_limit: int,
    routing_limit: int,
    readiness_baseline_limit: int,
    eco_limit: int,
    user: CurrentUser,
    db: Session,
) -> ItemCockpitResponse:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    generated_at = datetime.utcnow()

    # Impact summary (where-used + baselines + e-sign manifest/signatures).
    impact_svc = ImpactAnalysisService(db)
    user_view = CurrentUserView(
        id=int(user.id),
        roles=list(user.roles or []),
        is_superuser=bool(getattr(user, "is_superuser", False)),
    )
    where_used = impact_svc.where_used_summary(
        item_id=item_id,
        recursive=where_used_recursive,
        max_levels=where_used_max_levels,
        limit=where_used_limit,
    )
    baselines = impact_svc.baselines_summary(item_id=item_id, user=user_view, limit=baseline_limit)
    esign = impact_svc.esign_summary(item_id=item_id, limit=signature_limit)
    impact_summary = ImpactSummaryResponse(
        item_id=item_id,
        generated_at=datetime.utcnow(),
        where_used=WhereUsedSummary(**(where_used or {})),
        baselines=BaselinesSummary(**(baselines or {})),
        esign=ESignSummary(**(esign or {})),
    )

    # Release readiness (strategy-based diagnostics aggregation).
    readiness_svc = ReleaseReadinessService(db)
    readiness_payload = readiness_svc.get_item_release_readiness(
        item_id=item_id,
        ruleset_id=ruleset_id,
        mbom_limit=mbom_limit,
        routing_limit=routing_limit,
        baseline_limit=readiness_baseline_limit,
    )
    release_readiness = _build_response(payload=readiness_payload, ruleset_id=ruleset_id)

    # Open ECOs affecting this item (product_id = item_id), excluding terminal states.
    eco_svc = ECOService(db)
    ecos = eco_svc.list_ecos(product_id=item_id, limit=eco_limit, offset=0)
    hits: List[OpenEcoHit] = []
    for eco in ecos or []:
        state = (getattr(eco, "state", None) or "")
        if state.strip().lower() in {"done", "canceled"}:
            continue
        hits.append(
            OpenEcoHit(
                id=str(getattr(eco, "id", "")),
                name=str(getattr(eco, "name", "")),
                state=state or None,
                stage_id=getattr(eco, "stage_id", None),
                priority=getattr(eco, "priority", None),
                updated_at=getattr(eco, "updated_at", None),
                created_at=getattr(eco, "created_at", None),
            )
        )

    links = CockpitLinks(
        impact_export=f"/api/v1/impact/items/{item_id}/summary/export?export_format=zip",
        release_readiness_export=(
            f"/api/v1/release-readiness/items/{item_id}/export?export_format=zip&ruleset_id={ruleset_id}"
        ),
    )

    return ItemCockpitResponse(
        item=_serialize_item_subset(item),
        generated_at=generated_at,
        impact_summary=impact_summary,
        release_readiness=release_readiness,
        open_ecos=OpenEcosSummary(total=len(hits), hits=hits),
        links=links,
    )


@item_cockpit_router.get("/{item_id}/cockpit", response_model=ItemCockpitResponse)
def get_item_cockpit(
    item_id: str,
    ruleset_id: str = Query("readiness"),
    where_used_recursive: bool = Query(False),
    where_used_max_levels: int = Query(10, ge=1, le=50),
    where_used_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    signature_limit: int = Query(20, ge=0, le=200),
    mbom_limit: int = Query(20, ge=0, le=200),
    routing_limit: int = Query(20, ge=0, le=200),
    readiness_baseline_limit: int = Query(20, ge=0, le=200),
    eco_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemCockpitResponse:
    _ensure_admin(user)
    try:
        return _build_cockpit(
            item_id=item_id,
            ruleset_id=ruleset_id,
            where_used_recursive=where_used_recursive,
            where_used_max_levels=where_used_max_levels,
            where_used_limit=where_used_limit,
            baseline_limit=baseline_limit,
            signature_limit=signature_limit,
            mbom_limit=mbom_limit,
            routing_limit=routing_limit,
            readiness_baseline_limit=readiness_baseline_limit,
            eco_limit=eco_limit,
            user=user,
            db=db,
        )
    except ValueError as exc:
        # Most config errors are raised as ValueError by downstream services.
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@item_cockpit_router.get("/{item_id}/cockpit/export")
def export_item_cockpit(
    item_id: str,
    export_format: str = Query("zip", description="zip|json"),
    ruleset_id: str = Query("readiness"),
    where_used_recursive: bool = Query(False),
    where_used_max_levels: int = Query(10, ge=1, le=50),
    where_used_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    signature_limit: int = Query(20, ge=0, le=200),
    mbom_limit: int = Query(20, ge=0, le=200),
    routing_limit: int = Query(20, ge=0, le=200),
    readiness_baseline_limit: int = Query(20, ge=0, le=200),
    eco_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    _ensure_admin(user)
    cockpit = _build_cockpit(
        item_id=item_id,
        ruleset_id=ruleset_id,
        where_used_recursive=where_used_recursive,
        where_used_max_levels=where_used_max_levels,
        where_used_limit=where_used_limit,
        baseline_limit=baseline_limit,
        signature_limit=signature_limit,
        mbom_limit=mbom_limit,
        routing_limit=routing_limit,
        readiness_baseline_limit=readiness_baseline_limit,
        eco_limit=eco_limit,
        user=user,
        db=db,
    )

    fmt = (export_format or "").strip().lower()
    payload = cockpit.model_dump(mode="json")

    if fmt in {"json", "application/json"}:
        content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
        headers = {
            "Content-Disposition": f'attachment; filename="item-cockpit-{item_id}.json"'
        }
        return Response(content=content, media_type="application/json", headers=headers)

    if fmt != "zip":
        raise HTTPException(status_code=400, detail="Unsupported export format")

    where_used_rows = [hit.model_dump(mode="json") for hit in (cockpit.impact_summary.where_used.hits or [])]
    baselines_rows = [hit.model_dump(mode="json") for hit in (cockpit.impact_summary.baselines.hits or [])]
    signatures_rows = [
        hit.model_dump(mode="json") for hit in (cockpit.impact_summary.esign.latest_signatures or [])
    ]

    resources_rows: List[Dict[str, Any]] = []
    errors_rows: List[Dict[str, Any]] = []
    warnings_rows: List[Dict[str, Any]] = []

    for res in cockpit.release_readiness.resources or []:
        diag = res.diagnostics
        resources_rows.append(
            {
                "kind": res.kind,
                "name": res.name,
                "state": res.state,
                "resource_type": diag.resource_type,
                "resource_id": diag.resource_id,
                "ruleset_id": diag.ruleset_id,
                "ok": diag.ok,
                "error_count": len(diag.errors or []),
                "warning_count": len(diag.warnings or []),
            }
        )
        for issue in diag.errors or []:
            errors_rows.append(
                {
                    "kind": res.kind,
                    "resource_type": diag.resource_type,
                    "resource_id": diag.resource_id,
                    "ruleset_id": diag.ruleset_id,
                    "code": issue.code,
                    "rule_id": issue.rule_id,
                    "message": issue.message,
                    "details": issue.details,
                }
            )
        for issue in diag.warnings or []:
            warnings_rows.append(
                {
                    "kind": res.kind,
                    "resource_type": diag.resource_type,
                    "resource_id": diag.resource_id,
                    "ruleset_id": diag.ruleset_id,
                    "code": issue.code,
                    "rule_id": issue.rule_id,
                    "message": issue.message,
                    "details": issue.details,
                }
            )

    eco_rows = [hit.model_dump(mode="json") for hit in (cockpit.open_ecos.hits or [])]

    bundle = _zip_bytes(
        files={
            "cockpit.json": json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode(
                "utf-8"
            ),
            "where_used.csv": _csv_bytes(
                rows=where_used_rows,
                columns=[
                    "parent_id",
                    "parent_number",
                    "parent_name",
                    "relationship_id",
                    "level",
                    "line",
                ],
            ),
            "baselines.csv": _csv_bytes(
                rows=baselines_rows,
                columns=[
                    "baseline_id",
                    "name",
                    "baseline_number",
                    "baseline_type",
                    "scope",
                    "state",
                    "root_item_id",
                    "created_at",
                    "released_at",
                ],
            ),
            "signatures.csv": _csv_bytes(
                rows=signatures_rows,
                columns=["id", "meaning", "status", "signed_at", "signer_username"],
            ),
            "readiness_resources.csv": _csv_bytes(
                rows=resources_rows,
                columns=[
                    "kind",
                    "name",
                    "state",
                    "resource_type",
                    "resource_id",
                    "ruleset_id",
                    "ok",
                    "error_count",
                    "warning_count",
                ],
            ),
            "readiness_errors.csv": _csv_bytes(
                rows=errors_rows,
                columns=[
                    "kind",
                    "resource_type",
                    "resource_id",
                    "ruleset_id",
                    "code",
                    "rule_id",
                    "message",
                    "details",
                ],
            ),
            "readiness_warnings.csv": _csv_bytes(
                rows=warnings_rows,
                columns=[
                    "kind",
                    "resource_type",
                    "resource_id",
                    "ruleset_id",
                    "code",
                    "rule_id",
                    "message",
                    "details",
                ],
            ),
            "open_ecos.csv": _csv_bytes(
                rows=eco_rows,
                columns=[
                    "id",
                    "name",
                    "state",
                    "stage_id",
                    "priority",
                    "updated_at",
                    "created_at",
                ],
            ),
            "README.txt": (
                "YuantusPLM item cockpit export bundle\n"
                f"item_id={item_id}\n"
                f"generated_at={cockpit.generated_at.isoformat()}\n"
            ).encode("utf-8"),
        }
    )

    headers = {"Content-Disposition": f'attachment; filename="item-cockpit-{item_id}.zip"'}
    return StreamingResponse(io.BytesIO(bundle), media_type="application/zip", headers=headers)

