from __future__ import annotations

from datetime import datetime
import csv
import io
import json
from typing import Any, Dict, List, Optional
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi.responses import Response, StreamingResponse

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


def _build_response(*, payload: Dict[str, Any], ruleset_id: str) -> ReleaseReadinessResponse:
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
        item_id=str(payload.get("item_id") or ""),
        generated_at=payload.get("generated_at") or datetime.utcnow(),
        ruleset_id=str(payload.get("ruleset_id") or ruleset_id),
        summary=summary,
        resources=resources,
        esign_manifest=payload.get("esign_manifest"),
    )


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

    return _build_response(payload=payload, ruleset_id=ruleset_id)


@release_readiness_router.get("/items/{item_id}/export")
def export_item_release_readiness(
    item_id: str,
    export_format: str = Query("zip", description="zip|json"),
    ruleset_id: str = Query("readiness"),
    mbom_limit: int = Query(20, ge=0, le=200),
    routing_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
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

    response = _build_response(payload=payload, ruleset_id=ruleset_id)
    fmt = (export_format or "").strip().lower()

    json_payload = response.model_dump(mode="json")
    if fmt in {"json", "application/json"}:
        content = json.dumps(json_payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
        headers = {"Content-Disposition": f'attachment; filename="release-readiness-{item_id}.json"'}
        return Response(content=content, media_type="application/json", headers=headers)

    if fmt != "zip":
        raise HTTPException(status_code=400, detail="Unsupported export format")

    resources_rows: List[Dict[str, Any]] = []
    errors_rows: List[Dict[str, Any]] = []
    warnings_rows: List[Dict[str, Any]] = []

    for res in response.resources or []:
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

    bundle = _zip_bytes(
        files={
            "readiness.json": json.dumps(
                json_payload, ensure_ascii=False, default=str, indent=2
            ).encode("utf-8"),
            "resources.csv": _csv_bytes(
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
            "errors.csv": _csv_bytes(
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
            "warnings.csv": _csv_bytes(
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
            "esign_manifest.json": json.dumps(
                response.esign_manifest, ensure_ascii=False, default=str, indent=2
            ).encode("utf-8"),
            "README.txt": (
                "YuantusPLM release readiness export bundle\n"
                f"item_id={item_id}\n"
                f"generated_at={response.generated_at.isoformat()}\n"
            ).encode("utf-8"),
        }
    )

    headers = {
        "Content-Disposition": f'attachment; filename="release-readiness-{item_id}.zip"'
    }
    return StreamingResponse(io.BytesIO(bundle), media_type="application/zip", headers=headers)
