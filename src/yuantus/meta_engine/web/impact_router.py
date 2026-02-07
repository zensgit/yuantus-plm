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
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.impact_analysis_service import (
    CurrentUserView,
    ImpactAnalysisService,
)
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService


impact_router = APIRouter(prefix="/impact", tags=["Impact Analysis"])


class WhereUsedHit(BaseModel):
    parent_id: Optional[str] = None
    parent_number: Optional[str] = None
    parent_name: Optional[str] = None
    relationship_id: Optional[str] = None
    level: int = 1
    line: Dict[str, Any] = Field(default_factory=dict)


class WhereUsedSummary(BaseModel):
    total: int
    hits: List[WhereUsedHit] = Field(default_factory=list)
    recursive: bool
    max_levels: int


class BaselineHit(BaseModel):
    baseline_id: str
    name: str
    baseline_number: Optional[str] = None
    baseline_type: Optional[str] = None
    scope: Optional[str] = None
    state: Optional[str] = None
    root_item_id: Optional[str] = None
    created_at: Optional[datetime] = None
    released_at: Optional[datetime] = None


class BaselinesSummary(BaseModel):
    total: int
    hits: List[BaselineHit] = Field(default_factory=list)


class SignatureHit(BaseModel):
    id: str
    meaning: str
    status: str
    signed_at: Optional[datetime] = None
    signer_username: Optional[str] = None


class ESignManifestSummary(BaseModel):
    id: str
    generation: int
    is_complete: bool
    completed_at: Optional[datetime] = None


class ESignSummary(BaseModel):
    total: int
    valid: int
    revoked: int
    expired: int
    latest_signed_at: Optional[datetime] = None
    latest_signatures: List[SignatureHit] = Field(default_factory=list)
    latest_manifest: Optional[ESignManifestSummary] = None


class ImpactSummaryResponse(BaseModel):
    item_id: str
    generated_at: datetime
    where_used: WhereUsedSummary
    baselines: BaselinesSummary
    esign: ESignSummary


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
    # Excel-friendly with BOM.
    return buffer.getvalue().encode("utf-8-sig")


def _zip_bytes(*, files: Dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content or b"")
    return buffer.getvalue()


@impact_router.get("/items/{item_id}/summary", response_model=ImpactSummaryResponse)
def get_item_impact_summary(
    item_id: str,
    where_used_recursive: bool = Query(False, description="Include ancestors recursively"),
    where_used_max_levels: int = Query(10, ge=1, le=50),
    where_used_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    signature_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImpactSummaryResponse:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        item.item_type_id,
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = ImpactAnalysisService(db)
    user_view = CurrentUserView(
        id=int(user.id),
        roles=list(user.roles or []),
        is_superuser=bool(getattr(user, "is_superuser", False)),
    )

    where_used = service.where_used_summary(
        item_id=item_id,
        recursive=where_used_recursive,
        max_levels=where_used_max_levels,
        limit=where_used_limit,
    )
    baselines = service.baselines_summary(
        item_id=item_id,
        user=user_view,
        limit=baseline_limit,
    )
    esign = service.esign_summary(item_id=item_id, limit=signature_limit)

    return ImpactSummaryResponse(
        item_id=item_id,
        generated_at=datetime.utcnow(),
        where_used=WhereUsedSummary(**where_used),
        baselines=BaselinesSummary(**baselines),
        esign=ESignSummary(**esign),
    )


@impact_router.get("/items/{item_id}/summary/export")
def export_item_impact_summary(
    item_id: str,
    export_format: str = Query("zip", description="zip|json"),
    where_used_recursive: bool = Query(False, description="Include ancestors recursively"),
    where_used_max_levels: int = Query(10, ge=1, le=50),
    where_used_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    signature_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    summary = get_item_impact_summary(
        item_id=item_id,
        where_used_recursive=where_used_recursive,
        where_used_max_levels=where_used_max_levels,
        where_used_limit=where_used_limit,
        baseline_limit=baseline_limit,
        signature_limit=signature_limit,
        user=user,
        db=db,
    )

    fmt = (export_format or "").strip().lower()
    payload = summary.model_dump(mode="json")

    if fmt in {"json", "application/json"}:
        content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
        headers = {"Content-Disposition": f'attachment; filename="impact-summary-{item_id}.json"'}
        return Response(content=content, media_type="application/json", headers=headers)

    if fmt != "zip":
        raise HTTPException(status_code=400, detail="Unsupported export format")

    where_used_rows = [hit.model_dump(mode="json") for hit in (summary.where_used.hits or [])]
    baselines_rows = [hit.model_dump(mode="json") for hit in (summary.baselines.hits or [])]
    signatures_rows = [
        hit.model_dump(mode="json") for hit in (summary.esign.latest_signatures or [])
    ]

    bundle = _zip_bytes(
        files={
            "summary.json": json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode(
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
            "esign_signatures.csv": _csv_bytes(
                rows=signatures_rows,
                columns=[
                    "id",
                    "meaning",
                    "status",
                    "signed_at",
                    "signer_username",
                ],
            ),
            "esign_manifest.json": json.dumps(
                summary.esign.latest_manifest.model_dump(mode="json")
                if summary.esign.latest_manifest
                else None,
                ensure_ascii=False,
                default=str,
                indent=2,
            ).encode("utf-8"),
            "README.txt": (
                "YuantusPLM impact summary export bundle\n"
                f"item_id={item_id}\n"
                f"generated_at={summary.generated_at.isoformat()}\n"
            ).encode("utf-8"),
        }
    )

    headers = {"Content-Disposition": f'attachment; filename="impact-summary-{item_id}.zip"'}
    return StreamingResponse(io.BytesIO(bundle), media_type="application/zip", headers=headers)
