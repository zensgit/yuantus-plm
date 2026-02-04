from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.exceptions.handlers import PLMException
from yuantus.meta_engine.services.product_service import ProductDetailService


product_router = APIRouter(prefix="/products", tags=["Products"])


@product_router.get("/{item_id}")
def get_product_detail(
    item_id: str,
    include_versions: bool = Query(True, description="Include version history"),
    include_files: bool = Query(True, description="Include attached files"),
    include_version_files: bool = Query(
        False, description="Include files attached to the current version"
    ),
    include_bom_summary: bool = Query(
        False, description="Include BOM summary (counts/depth)"
    ),
    include_bom_obsolete_summary: bool = Query(
        False, description="Include obsolete BOM summary"
    ),
    bom_obsolete_recursive: bool = Query(
        True, description="Scan descendants for obsolete BOM summary"
    ),
    bom_obsolete_levels: int = Query(
        10, description="Max scan depth for obsolete summary (-1 for unlimited)"
    ),
    bom_summary_depth: int = Query(
        1, description="BOM summary depth for counts (1=direct children)"
    ),
    bom_effective_at: str = Query(
        "", description="Optional ISO datetime for BOM summary effectivity"
    ),
    include_bom_weight_rollup: bool = Query(
        False, description="Include BOM weight rollup summary"
    ),
    bom_weight_levels: int = Query(3, description="Explosion depth for weight rollup"),
    bom_weight_effective_at: str = Query(
        "", description="Optional ISO datetime for weight rollup effectivity"
    ),
    bom_weight_rounding: Optional[int] = Query(
        3, description="Rounding precision for weight rollup (None to skip)"
    ),
    include_where_used_summary: bool = Query(
        False, description="Include where-used summary"
    ),
    where_used_recursive: bool = Query(
        False, description="Include recursive where-used summary"
    ),
    where_used_max_levels: int = Query(5, description="Max levels for where-used"),
    include_document_summary: bool = Query(
        False, description="Include related document lifecycle summary"
    ),
    include_eco_summary: bool = Query(
        False, description="Include ECO summary for this product"
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = ProductDetailService(db, user_id=str(user.id), roles=user.roles)
    try:
        return service.get_detail(
            item_id,
            include_versions=include_versions,
            include_files=include_files,
            include_version_files=include_version_files,
            include_bom_summary=include_bom_summary,
            include_bom_obsolete_summary=include_bom_obsolete_summary,
            bom_obsolete_recursive=bom_obsolete_recursive,
            bom_obsolete_levels=bom_obsolete_levels,
            bom_summary_depth=bom_summary_depth,
            bom_effective_at=bom_effective_at or None,
            include_bom_weight_rollup=include_bom_weight_rollup,
            bom_weight_levels=bom_weight_levels,
            bom_weight_effective_at=bom_weight_effective_at or None,
            bom_weight_rounding=bom_weight_rounding,
            include_where_used_summary=include_where_used_summary,
            where_used_recursive=where_used_recursive,
            where_used_max_levels=where_used_max_levels,
            include_document_summary=include_document_summary,
            include_eco_summary=include_eco_summary,
        )
    except PLMException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
