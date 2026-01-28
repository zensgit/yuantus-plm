from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.configuration import ConfigOption, ConfigOptionSet
from yuantus.meta_engine.services.config_service import ConfigService

config_router = APIRouter(prefix="/config", tags=["Config"])


class OptionSetCreate(BaseModel):
    id: Optional[str] = None
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    item_type_id: Optional[str] = None
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None


class OptionSetUpdate(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    item_type_id: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class OptionCreate(BaseModel):
    id: Optional[str] = None
    key: str
    label: Optional[str] = None
    value: Optional[str] = None
    sort_order: int = 0
    is_default: bool = False
    extra: Optional[Dict[str, Any]] = None


class OptionUpdate(BaseModel):
    key: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    sort_order: Optional[int] = None
    is_default: Optional[bool] = None
    extra: Optional[Dict[str, Any]] = None


class OptionResponse(BaseModel):
    id: str
    option_set_id: str
    key: str
    label: Optional[str] = None
    value: Optional[str] = None
    sort_order: int
    is_default: bool
    extra: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OptionSetResponse(BaseModel):
    id: str
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    item_type_id: Optional[str] = None
    is_active: bool
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    options: List[OptionResponse] = Field(default_factory=list)


def _ensure_superuser(user: CurrentUser) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")


def _option_to_response(option: ConfigOption) -> OptionResponse:
    return OptionResponse(
        id=option.id,
        option_set_id=option.option_set_id,
        key=option.key,
        label=option.label,
        value=option.value,
        sort_order=option.sort_order or 0,
        is_default=bool(option.is_default),
        extra=option.extra,
        created_at=option.created_at,
        updated_at=option.updated_at,
    )


def _option_set_to_response(option_set: ConfigOptionSet, include_options: bool) -> OptionSetResponse:
    options: List[OptionResponse] = []
    if include_options:
        options = [_option_to_response(o) for o in option_set.options]
    return OptionSetResponse(
        id=option_set.id,
        name=option_set.name,
        label=option_set.label,
        description=option_set.description,
        item_type_id=option_set.item_type_id,
        is_active=bool(option_set.is_active),
        config=option_set.config or {},
        created_at=option_set.created_at,
        updated_at=option_set.updated_at,
        options=options,
    )


@config_router.get("/option-sets", response_model=List[OptionSetResponse])
async def list_option_sets(
    include_options: bool = Query(False, description="Include options in each option set"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    option_sets = service.list_option_sets()
    return [_option_set_to_response(o, include_options) for o in option_sets]


@config_router.get("/option-sets/{option_set_id}", response_model=OptionSetResponse)
async def get_option_set(
    option_set_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    option_set = service.get_option_set(option_set_id)
    if not option_set:
        raise HTTPException(status_code=404, detail="OptionSet not found")
    return _option_set_to_response(option_set, include_options=True)


@config_router.post("/option-sets", response_model=OptionSetResponse)
async def create_option_set(
    request: OptionSetCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    try:
        option_set = service.create_option_set(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _option_set_to_response(option_set, include_options=True)


@config_router.patch("/option-sets/{option_set_id}", response_model=OptionSetResponse)
async def update_option_set(
    option_set_id: str,
    request: OptionSetUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    option_set = service.get_option_set(option_set_id)
    if not option_set:
        raise HTTPException(status_code=404, detail="OptionSet not found")
    try:
        option_set = service.update_option_set(option_set, request.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _option_set_to_response(option_set, include_options=True)


@config_router.delete("/option-sets/{option_set_id}")
async def delete_option_set(
    option_set_id: str,
    force: bool = Query(False, description="Delete even if options exist"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    option_set = service.get_option_set(option_set_id)
    if not option_set:
        raise HTTPException(status_code=404, detail="OptionSet not found")
    try:
        service.delete_option_set(option_set, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "option_set_id": option_set_id}


@config_router.post("/option-sets/{option_set_id}/options", response_model=OptionResponse)
async def add_option(
    option_set_id: str,
    request: OptionCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    option_set = service.get_option_set(option_set_id)
    if not option_set:
        raise HTTPException(status_code=404, detail="OptionSet not found")
    try:
        option = service.add_option(option_set, request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _option_to_response(option)


@config_router.patch("/option-sets/{option_set_id}/options/{option_id}", response_model=OptionResponse)
async def update_option(
    option_set_id: str,
    option_id: str,
    request: OptionUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    option = db.get(ConfigOption, option_id)
    if not option or option.option_set_id != option_set_id:
        raise HTTPException(status_code=404, detail="Option not found")
    try:
        option = service.update_option(option, request.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _option_to_response(option)


@config_router.delete("/option-sets/{option_set_id}/options/{option_id}")
async def delete_option(
    option_set_id: str,
    option_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    option = db.get(ConfigOption, option_id)
    if not option or option.option_set_id != option_set_id:
        raise HTTPException(status_code=404, detail="Option not found")
    service = ConfigService(db)
    service.delete_option(option)
    return {"ok": True, "option_id": option_id}
