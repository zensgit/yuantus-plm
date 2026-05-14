"""
ECO impact and apply router slice.

R4 of the ECO router decomposition owns impact analysis, impact export,
BOM diff, apply execution, and apply diagnostics. Lifecycle actions such as
cancel/suspend/unsuspend/move-stage remain in the legacy ECO router.
"""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user, get_current_user_id_optional
from yuantus.database import get_db
from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.eco_export_service import EcoImpactExportService
from yuantus.meta_engine.services.eco_service import ECOService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.meta_engine.web.release_diagnostics_models import (
    ReleaseDiagnosticsResponse,
    issue_to_response,
)

eco_impact_apply_router = APIRouter(prefix="/eco", tags=["ECO"])


def _normalize_relationship_props(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    flattened: List[str] = []
    for raw in values:
        if raw is None:
            continue
        for part in str(raw).split(","):
            part = part.strip()
            if part:
                flattened.append(part)
    return flattened or None


def _ensure_can_apply_eco(service: ECOService, *, eco_id: str, user_id: int) -> None:
    try:
        service.permission_service.check_permission(
            user_id, "execute", "ECO", resource_id=eco_id, field="apply"
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=exc.to_dict()) from exc


def _ensure_can_read_eco_product_bom(
    db: Session,
    *,
    product: Item,
    user,
) -> None:
    perm = MetaPermissionService(db)
    if not perm.check_permission(
        product.item_type_id,
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


def _get_eco_product_or_404(db: Session, service: ECOService, eco_id: str):
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")
    if not eco.product_id:
        raise HTTPException(status_code=400, detail="ECO missing product_id")

    product = db.get(Item, eco.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return eco, product


@eco_impact_apply_router.get("/{eco_id}/impact", response_model=Dict[str, Any])
async def get_eco_impact(
    eco_id: str,
    include_files: bool = Query(False, description="Include file details"),
    include_bom_diff: bool = Query(False, description="Include BOM diff details"),
    include_version_diff: bool = Query(
        False, description="Include version property/file diffs"
    ),
    max_levels: int = Query(10, description="Explosion depth (-1 for unlimited)"),
    effective_at: Optional[datetime] = Query(None, description="Effectivity filter date"),
    include_child_fields: bool = Query(False, description="Include parent/child fields"),
    include_relationship_props: Optional[List[str]] = Query(
        None, description="Comma-separated relationship property whitelist"
    ),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get ECO impact analysis."""
    if max_levels < -1:
        raise HTTPException(status_code=400, detail="max_levels must be >= -1")

    include_props = _normalize_relationship_props(include_relationship_props)
    service = ECOService(db)
    _eco, product = _get_eco_product_or_404(db, service, eco_id)
    _ensure_can_read_eco_product_bom(db, product=product, user=user)

    try:
        return service.analyze_impact(
            eco_id,
            include_files=include_files,
            include_bom_diff=include_bom_diff,
            include_version_diff=include_version_diff,
            max_levels=max_levels,
            effective_at=effective_at,
            include_relationship_props=include_props,
            include_child_fields=include_child_fields,
            compare_mode=compare_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@eco_impact_apply_router.get("/{eco_id}/impact/export")
async def export_eco_impact(
    eco_id: str,
    format: str = Query("csv", description="csv|xlsx|pdf|json"),
    include_files: bool = Query(True, description="Include file details"),
    include_bom_diff: bool = Query(True, description="Include BOM diff details"),
    include_version_diff: bool = Query(True, description="Include version diffs"),
    max_levels: int = Query(10, description="Explosion depth (-1 for unlimited)"),
    effective_at: Optional[datetime] = Query(None, description="Effectivity filter date"),
    include_child_fields: bool = Query(True, description="Include parent/child fields"),
    include_relationship_props: Optional[List[str]] = Query(
        None, description="Comma-separated relationship property whitelist"
    ),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if max_levels < -1:
        raise HTTPException(status_code=400, detail="max_levels must be >= -1")

    include_props = _normalize_relationship_props(include_relationship_props)
    service = ECOService(db)
    _eco, product = _get_eco_product_or_404(db, service, eco_id)
    _ensure_can_read_eco_product_bom(db, product=product, user=user)

    try:
        impact = service.analyze_impact(
            eco_id,
            include_files=include_files,
            include_bom_diff=include_bom_diff,
            include_version_diff=include_version_diff,
            max_levels=max_levels,
            effective_at=effective_at,
            include_relationship_props=include_props,
            include_child_fields=include_child_fields,
            compare_mode=compare_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    fmt = (format or "").strip().lower()
    if fmt in {"json", "application/json"}:
        return impact

    exporter = EcoImpactExportService(impact)
    if fmt in {"csv"}:
        data = exporter.to_csv().encode("utf-8-sig")
        media_type = "text/csv"
        ext = "csv"
    elif fmt in {"xlsx", "excel"}:
        data = exporter.to_xlsx()
        media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        ext = "xlsx"
    elif fmt in {"pdf"}:
        data = exporter.to_pdf()
        media_type = "application/pdf"
        ext = "pdf"
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format")

    filename = f"eco-impact-{eco_id}.{ext}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(data), media_type=media_type, headers=headers)


@eco_impact_apply_router.get("/{eco_id}/bom-diff", response_model=Dict[str, Any])
async def get_eco_bom_diff(
    eco_id: str,
    max_levels: int = Query(10, description="Explosion depth (-1 for unlimited)"),
    effective_at: Optional[datetime] = Query(None, description="Effectivity filter date"),
    include_child_fields: bool = Query(False, description="Include parent/child fields"),
    include_relationship_props: Optional[List[str]] = Query(
        None, description="Comma-separated relationship property whitelist"
    ),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get BOM redline diff between ECO source and target versions."""
    if max_levels < -1:
        raise HTTPException(status_code=400, detail="max_levels must be >= -1")

    include_props = _normalize_relationship_props(include_relationship_props)
    service = ECOService(db)
    _eco, product = _get_eco_product_or_404(db, service, eco_id)
    _ensure_can_read_eco_product_bom(db, product=product, user=user)

    try:
        return service.get_bom_diff(
            eco_id,
            max_levels=max_levels,
            effective_at=effective_at,
            include_relationship_props=include_props,
            include_child_fields=include_child_fields,
            compare_mode=compare_mode,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@eco_impact_apply_router.post("/{eco_id}/apply", response_model=Dict[str, Any])
async def apply_eco(
    eco_id: str,
    ruleset_id: str = Query("default"),
    force: bool = Query(False),
    ignore_conflicts: bool = Query(False),
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Apply the ECO changes.
    Sets the target version as current and marks ECO as done.
    """
    service = ECOService(db)
    try:
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")

        if not force:
            eco = service.get_eco(eco_id)
            if eco:
                _ensure_can_apply_eco(service, eco_id=eco_id, user_id=int(user_id))
            diagnostics = service.get_apply_diagnostics(
                eco_id,
                int(user_id),
                ruleset_id=ruleset_id,
                ignore_conflicts=ignore_conflicts,
            )
            err_count = len(diagnostics.get("errors") or [])
            warn_count = len(diagnostics.get("warnings") or [])
            if err_count:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"ECO apply blocked: errors={err_count}, warnings={warn_count}. "
                        f"Run /api/v1/eco/{eco_id}/apply-diagnostics?ruleset_id={ruleset_id} for details."
                    ),
                )

        success = service.action_apply(
            eco_id,
            int(user_id),
            ignore_conflicts=ignore_conflicts,
        )
        db.commit()
        return {"success": success, "message": "ECO applied successfully"}
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=exc.to_dict()) from exc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@eco_impact_apply_router.get(
    "/{eco_id}/apply-diagnostics", response_model=ReleaseDiagnosticsResponse
)
async def get_eco_apply_diagnostics(
    eco_id: str,
    ruleset_id: str = Query("default"),
    ignore_conflicts: bool = Query(False),
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
) -> ReleaseDiagnosticsResponse:
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if eco:
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        _ensure_can_apply_eco(service, eco_id=eco_id, user_id=int(user_id))

    try:
        diagnostics = service.get_apply_diagnostics(
            eco_id,
            int(user_id or 0),
            ruleset_id=ruleset_id,
            ignore_conflicts=ignore_conflicts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    errors = [issue_to_response(issue) for issue in (diagnostics.get("errors") or [])]
    warnings = [issue_to_response(issue) for issue in (diagnostics.get("warnings") or [])]
    return ReleaseDiagnosticsResponse(
        ok=len(errors) == 0,
        resource_type="eco",
        resource_id=eco_id,
        ruleset_id=str(diagnostics.get("ruleset_id") or ruleset_id),
        errors=errors,
        warnings=warnings,
    )
