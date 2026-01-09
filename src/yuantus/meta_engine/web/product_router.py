from __future__ import annotations

from typing import Any, Dict

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
        )
    except PLMException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
