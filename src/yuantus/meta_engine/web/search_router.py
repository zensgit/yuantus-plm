from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from yuantus.database import get_db
from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.meta_engine.services.search_service import SearchService

search_router = APIRouter(prefix="/search", tags=["Search"])


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    roles = set(user.roles or [])
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


class SearchStatusResponse(BaseModel):
    engine: str
    enabled: bool
    index: str
    index_exists: bool = False


class SearchReindexRequest(BaseModel):
    item_type_id: Optional[str] = Field(default=None)
    reset: bool = Field(default=False)
    limit: Optional[int] = Field(default=None, ge=1)
    batch_size: int = Field(default=200, ge=1, le=2000)


class SearchReindexResponse(BaseModel):
    ok: bool
    engine: str
    index: str
    indexed: int
    reset: bool
    item_type_id: Optional[str] = None
    note: Optional[str] = None


class EcoReindexRequest(BaseModel):
    state: Optional[str] = Field(default=None)
    reset: bool = Field(default=False)
    limit: Optional[int] = Field(default=None, ge=1)
    batch_size: int = Field(default=200, ge=1, le=2000)


class EcoReindexResponse(BaseModel):
    ok: bool
    engine: str
    index: str
    indexed: int
    reset: bool
    state: Optional[str] = None
    note: Optional[str] = None


@search_router.get("/")
def search_items(
    q: str,
    item_type: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SearchService(db)
    filters: Dict[str, Any] = {}
    if item_type:
        filters["item_type_id"] = item_type
    if state:
        filters["state"] = state
    return service.search(q, filters=filters, limit=limit)


@search_router.get("/ecos")
def search_ecos(
    q: str = Query("", description="Search text for ECO id/name/description"),
    state: Optional[str] = Query(None, description="Filter by ECO state"),
    limit: int = Query(20, ge=1, le=200),
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SearchService(db)
    return service.search_ecos(q, state=state, limit=limit)


@search_router.get("/ecos/status", response_model=SearchStatusResponse)
def search_ecos_status(
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SearchStatusResponse:
    service = SearchService(db)
    return SearchStatusResponse(**service.eco_status())


@search_router.post("/ecos/reindex", response_model=EcoReindexResponse)
def search_ecos_reindex(
    req: EcoReindexRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> EcoReindexResponse:
    service = SearchService(db)
    result = service.reindex_ecos(
        state=req.state,
        reset=req.reset,
        limit=req.limit,
        batch_size=req.batch_size,
    )
    return EcoReindexResponse(**result)


@search_router.get("/status", response_model=SearchStatusResponse)
def search_status(
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SearchStatusResponse:
    service = SearchService(db)
    return SearchStatusResponse(**service.status())


@search_router.post("/reindex", response_model=SearchReindexResponse)
def search_reindex(
    req: SearchReindexRequest,
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SearchReindexResponse:
    service = SearchService(db)
    result = service.reindex_items(
        item_type_id=req.item_type_id,
        reset=req.reset,
        limit=req.limit,
        batch_size=req.batch_size,
    )
    return SearchReindexResponse(**result)
