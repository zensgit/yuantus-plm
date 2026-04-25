from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.reports.search_service import SavedSearchService

report_saved_search_router = APIRouter(prefix="/reports", tags=["Reports"])


class SavedSearchCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_public: bool = False
    item_type_id: Optional[str] = None
    criteria: Dict[str, Any] = Field(default_factory=dict)
    display_columns: Optional[List[str]] = None
    page_size: int = Field(default=25, ge=1, le=1000)


class SavedSearchUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    is_public: Optional[bool] = None
    item_type_id: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    display_columns: Optional[List[str]] = None
    page_size: Optional[int] = Field(default=None, ge=1, le=1000)


class SavedSearchResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: Optional[int]
    is_public: bool
    item_type_id: Optional[str]
    criteria: Dict[str, Any]
    display_columns: Optional[List[str]]
    page_size: int
    use_count: int
    last_used_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


def _is_admin(user: CurrentUser) -> bool:
    if bool(getattr(user, "is_superuser", False)):
        return True
    roles = {str(role).strip().lower() for role in (user.roles or []) if str(role).strip()}
    return "admin" in roles or "superuser" in roles


def _to_saved_search_response(saved) -> SavedSearchResponse:
    return SavedSearchResponse(
        id=saved.id,
        name=saved.name,
        description=saved.description,
        owner_id=saved.owner_id,
        is_public=bool(saved.is_public),
        item_type_id=saved.item_type_id,
        criteria=saved.criteria or {},
        display_columns=saved.display_columns,
        page_size=saved.page_size or 25,
        use_count=saved.use_count or 0,
        last_used_at=saved.last_used_at,
        created_at=saved.created_at,
        updated_at=saved.updated_at,
    )


@report_saved_search_router.post("/saved-searches", response_model=SavedSearchResponse)
def create_saved_search(
    req: SavedSearchCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearchResponse:
    service = SavedSearchService(db)
    saved = service.create_saved_search(
        name=req.name,
        description=req.description,
        owner_id=user.id,
        is_public=req.is_public,
        item_type_id=req.item_type_id,
        criteria=req.criteria,
        display_columns=req.display_columns,
        page_size=req.page_size,
    )
    return _to_saved_search_response(saved)


@report_saved_search_router.get("/saved-searches", response_model=Dict[str, Any])
def list_saved_searches(
    include_public: bool = Query(True),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SavedSearchService(db)
    items = service.list_saved_searches(owner_id=user.id, include_public=include_public)
    return {"items": [_to_saved_search_response(ss).model_dump() for ss in items]}


@report_saved_search_router.get("/saved-searches/{saved_search_id}", response_model=SavedSearchResponse)
def get_saved_search(
    saved_search_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearchResponse:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and not saved.is_public and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return _to_saved_search_response(saved)


@report_saved_search_router.patch("/saved-searches/{saved_search_id}", response_model=SavedSearchResponse)
def update_saved_search(
    saved_search_id: str,
    req: SavedSearchUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedSearchResponse:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    updated = service.update_saved_search(
        saved_search_id,
        name=req.name,
        description=req.description,
        is_public=req.is_public,
        item_type_id=req.item_type_id,
        criteria=req.criteria,
        display_columns=req.display_columns,
        page_size=req.page_size,
    )
    return _to_saved_search_response(updated)


@report_saved_search_router.delete("/saved-searches/{saved_search_id}", response_model=Dict[str, Any])
def delete_saved_search(
    saved_search_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    service.delete_saved_search(saved_search_id)
    return {"status": "deleted", "id": saved_search_id}


@report_saved_search_router.post("/saved-searches/{saved_search_id}/run", response_model=Dict[str, Any])
def run_saved_search(
    saved_search_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    service = SavedSearchService(db)
    saved = service.get_saved_search(saved_search_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Saved search not found")
    if not _is_admin(user) and not saved.is_public and saved.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    return service.run_saved_search(
        saved_search_id,
        page=page,
        page_size=page_size or None,
    )
