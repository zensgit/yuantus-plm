from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.release_readiness_service import ReleaseReadinessService
from yuantus.meta_engine.web.release_diagnostics_models import (
    ReleaseDiagnosticsResponse,
    issue_to_response,
)


release_readiness_router = APIRouter(
    prefix="/release-readiness",
    tags=["Release Readiness"],
)


def _ensure_admin(user: CurrentUser) -> None:
    roles = {str(r).lower() for r in (user.roles or [])}
    if user.is_superuser or ("admin" in roles) or ("superuser" in roles):
        return
    raise HTTPException(status_code=403, detail="Admin permission required")


class KindSummary(BaseModel):
    resources: int = 0
    ok_resources: int = 0
    error_count: int = 0
    warning_count: int = 0


class ReadinessSummary(BaseModel):
    ok: bool
    resources: int = 0
    ok_resources: int = 0
    error_count: int = 0
    warning_count: int = 0
    by_kind: Dict[str, KindSummary] = Field(default_factory=dict)


class ReadinessResource(BaseModel):
    kind: str
    name: Optional[str] = None
    state: Optional[str] = None
    diagnostics: ReleaseDiagnosticsResponse


class ReleaseReadinessResponse(BaseModel):
    item_id: str
    generated_at: datetime
    ruleset_id: str
    summary: ReadinessSummary
    resources: List[ReadinessResource] = Field(default_factory=list)
    esign_manifest: Optional[Dict[str, Any]] = None


@release_readiness_router.get("/items/{item_id}", response_model=ReleaseReadinessResponse)
def get_item_release_readiness(
    item_id: str,
    ruleset_id: str = Query("readiness"),
    mbom_limit: int = Query(20, ge=0, le=200),
    routing_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReleaseReadinessResponse:
    _ensure_admin(user)

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    service = ReleaseReadinessService(db)
    try:
        payload = service.get_item_release_readiness(
            item_id=item_id,
            ruleset_id=ruleset_id,
            mbom_limit=mbom_limit,
            routing_limit=routing_limit,
            baseline_limit=baseline_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resources: List[ReadinessResource] = []
    for entry in payload.get("resources") or []:
        errors = [issue_to_response(issue) for issue in (entry.get("errors") or [])]
        warnings = [issue_to_response(issue) for issue in (entry.get("warnings") or [])]
        diag = ReleaseDiagnosticsResponse(
            ok=len(errors) == 0,
            resource_type=str(entry.get("resource_type") or "unknown"),
            resource_id=str(entry.get("resource_id") or ""),
            ruleset_id=str(entry.get("ruleset_id") or ruleset_id),
            errors=errors,
            warnings=warnings,
        )
        resources.append(
            ReadinessResource(
                kind=str(entry.get("kind") or ""),
                name=entry.get("name"),
                state=entry.get("state"),
                diagnostics=diag,
            )
        )

    summary_payload = payload.get("summary") or {}
    by_kind_payload = summary_payload.get("by_kind") or {}
    by_kind: Dict[str, KindSummary] = {}
    for kind, values in by_kind_payload.items():
        by_kind[str(kind)] = KindSummary(**(values or {}))

    summary = ReadinessSummary(
        ok=bool(summary_payload.get("ok")),
        resources=int(summary_payload.get("resources") or 0),
        ok_resources=int(summary_payload.get("ok_resources") or 0),
        error_count=int(summary_payload.get("error_count") or 0),
        warning_count=int(summary_payload.get("warning_count") or 0),
        by_kind=by_kind,
    )

    return ReleaseReadinessResponse(
        item_id=item_id,
        generated_at=payload.get("generated_at") or datetime.utcnow(),
        ruleset_id=str(payload.get("ruleset_id") or ruleset_id),
        summary=summary,
        resources=resources,
        esign_manifest=payload.get("esign_manifest"),
    )

