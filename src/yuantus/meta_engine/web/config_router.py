from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.configuration import (
    ConfigOption,
    ConfigOptionSet,
    ProductConfiguration,
    VariantRule,
)
from yuantus.meta_engine.services.config_service import ConfigService

config_router = APIRouter(prefix="/config", tags=["Config"])


class OptionSetCreate(BaseModel):
    id: Optional[str] = None
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    value_type: Optional[str] = None
    allow_multiple: bool = False
    is_required: bool = False
    default_value: Optional[str] = None
    sequence: int = 0
    item_type_id: Optional[str] = None
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None


class OptionSetUpdate(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    value_type: Optional[str] = None
    allow_multiple: Optional[bool] = None
    is_required: Optional[bool] = None
    default_value: Optional[str] = None
    sequence: Optional[int] = None
    item_type_id: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class OptionCreate(BaseModel):
    id: Optional[str] = None
    key: str
    label: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    ref_item_id: Optional[str] = None
    sort_order: int = 0
    is_default: bool = False
    is_active: bool = True
    extra: Optional[Dict[str, Any]] = None


class OptionUpdate(BaseModel):
    key: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    ref_item_id: Optional[str] = None
    sort_order: Optional[int] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    extra: Optional[Dict[str, Any]] = None


class OptionResponse(BaseModel):
    id: str
    option_set_id: str
    key: str
    label: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    ref_item_id: Optional[str] = None
    sort_order: int
    is_default: bool
    is_active: bool
    extra: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class OptionSetResponse(BaseModel):
    id: str
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    value_type: Optional[str] = None
    allow_multiple: bool
    is_required: bool
    default_value: Optional[str] = None
    sequence: int
    item_type_id: Optional[str] = None
    is_active: bool
    config: Dict[str, Any] = Field(default_factory=dict)
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    options: List[OptionResponse] = Field(default_factory=list)


class VariantRuleCreate(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    parent_item_type_id: Optional[str] = None
    parent_item_id: Optional[str] = None
    condition: Dict[str, Any]
    action_type: str
    target_item_id: Optional[str] = None
    target_relationship_id: Optional[str] = None
    action_params: Optional[Dict[str, Any]] = None
    priority: int = 100
    is_active: bool = True


class VariantRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_item_type_id: Optional[str] = None
    parent_item_id: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    action_type: Optional[str] = None
    target_item_id: Optional[str] = None
    target_relationship_id: Optional[str] = None
    action_params: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class VariantRuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parent_item_type_id: Optional[str] = None
    parent_item_id: Optional[str] = None
    condition: Dict[str, Any]
    action_type: str
    target_item_id: Optional[str] = None
    target_relationship_id: Optional[str] = None
    action_params: Optional[Dict[str, Any]] = None
    priority: int
    is_active: bool
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None


class ProductConfigurationCreate(BaseModel):
    id: Optional[str] = None
    product_item_id: str
    name: str
    description: Optional[str] = None
    selections: Dict[str, Any]
    state: Optional[str] = None
    version: Optional[int] = None


class ProductConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    selections: Optional[Dict[str, Any]] = None
    state: Optional[str] = None
    version: Optional[int] = None


class ProductConfigurationResponse(BaseModel):
    id: str
    product_item_id: str
    name: str
    description: Optional[str] = None
    selections: Dict[str, Any]
    effective_bom_cache: Optional[Dict[str, Any]] = None
    cache_updated_at: Optional[datetime] = None
    state: Optional[str] = None
    version: int
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    released_by_id: Optional[int] = None


class EffectiveBomRequest(BaseModel):
    product_item_id: str
    selections: Dict[str, Any]
    levels: int = 10
    effective_date: Optional[datetime] = None


class ValidateSelectionsRequest(BaseModel):
    product_item_id: str
    selections: Dict[str, Any]


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
        description=option.description,
        ref_item_id=option.ref_item_id,
        sort_order=option.sort_order or 0,
        is_default=bool(option.is_default),
        is_active=bool(option.is_active),
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
        value_type=option_set.value_type,
        allow_multiple=bool(option_set.allow_multiple),
        is_required=bool(option_set.is_required),
        default_value=option_set.default_value,
        sequence=int(option_set.sequence or 0),
        item_type_id=option_set.item_type_id,
        is_active=bool(option_set.is_active),
        config=option_set.config or {},
        created_by_id=option_set.created_by_id,
        created_at=option_set.created_at,
        updated_at=option_set.updated_at,
        options=options,
    )


def _rule_to_response(rule: VariantRule) -> VariantRuleResponse:
    return VariantRuleResponse(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        parent_item_type_id=rule.parent_item_type_id,
        parent_item_id=rule.parent_item_id,
        condition=rule.condition or {},
        action_type=rule.action_type,
        target_item_id=rule.target_item_id,
        target_relationship_id=rule.target_relationship_id,
        action_params=rule.action_params or {},
        priority=rule.priority or 0,
        is_active=bool(rule.is_active),
        created_by_id=rule.created_by_id,
        created_at=rule.created_at,
    )


def _config_to_response(config: ProductConfiguration) -> ProductConfigurationResponse:
    return ProductConfigurationResponse(
        id=config.id,
        product_item_id=config.product_item_id,
        name=config.name,
        description=config.description,
        selections=config.selections or {},
        effective_bom_cache=config.effective_bom_cache,
        cache_updated_at=config.cache_updated_at,
        state=config.state,
        version=config.version or 1,
        created_by_id=config.created_by_id,
        created_at=config.created_at,
        released_at=config.released_at,
        released_by_id=config.released_by_id,
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
        payload = request.model_dump()
        payload["created_by_id"] = int(user.id)
        option_set = service.create_option_set(payload)
        db.commit()
    except ValueError as exc:
        db.rollback()
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
        db.commit()
    except ValueError as exc:
        db.rollback()
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
        db.commit()
    except ValueError as exc:
        db.rollback()
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
        db.commit()
    except ValueError as exc:
        db.rollback()
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
        db.commit()
    except ValueError as exc:
        db.rollback()
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
    try:
        service.delete_option(option)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "option_id": option_id}


# ----------------------------------------------------------------------
# Variant rules
# ----------------------------------------------------------------------


@config_router.get("/variant-rules", response_model=List[VariantRuleResponse])
async def list_variant_rules(
    parent_item_id: Optional[str] = Query(None),
    parent_item_type_id: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    rules = service.list_variant_rules(
        parent_item_id=parent_item_id,
        parent_item_type_id=parent_item_type_id,
        include_inactive=include_inactive,
    )
    return [_rule_to_response(r) for r in rules]


@config_router.get("/variant-rules/{rule_id}", response_model=VariantRuleResponse)
async def get_variant_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    rule = service.get_variant_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="VariantRule not found")
    return _rule_to_response(rule)


@config_router.post("/variant-rules", response_model=VariantRuleResponse)
async def create_variant_rule(
    request: VariantRuleCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    try:
        payload = request.model_dump()
        payload["created_by_id"] = int(user.id)
        rule = service.create_variant_rule(payload)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _rule_to_response(rule)


@config_router.patch("/variant-rules/{rule_id}", response_model=VariantRuleResponse)
async def update_variant_rule(
    rule_id: str,
    request: VariantRuleUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    rule = service.get_variant_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="VariantRule not found")
    try:
        rule = service.update_variant_rule(rule, request.model_dump(exclude_unset=True))
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _rule_to_response(rule)


@config_router.delete("/variant-rules/{rule_id}")
async def delete_variant_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_superuser(user)
    service = ConfigService(db)
    rule = service.get_variant_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="VariantRule not found")
    try:
        service.delete_variant_rule(rule)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "rule_id": rule_id}


# ----------------------------------------------------------------------
# Product configurations
# ----------------------------------------------------------------------


@config_router.get("/configurations", response_model=List[ProductConfigurationResponse])
async def list_product_configurations(
    product_item_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    items = service.list_product_configurations(product_item_id=product_item_id)
    return [_config_to_response(c) for c in items]


@config_router.get("/configurations/{config_id}", response_model=ProductConfigurationResponse)
async def get_product_configuration(
    config_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    config = service.get_product_configuration(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return _config_to_response(config)


@config_router.post("/configurations", response_model=ProductConfigurationResponse)
async def create_product_configuration(
    request: ProductConfigurationCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    try:
        payload = request.model_dump()
        payload["created_by_id"] = int(user.id)
        config = service.create_product_configuration(payload)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _config_to_response(config)


@config_router.patch("/configurations/{config_id}", response_model=ProductConfigurationResponse)
async def update_product_configuration(
    config_id: str,
    request: ProductConfigurationUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    config = service.get_product_configuration(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    try:
        config = service.update_product_configuration(config, request.model_dump(exclude_unset=True))
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _config_to_response(config)


@config_router.post("/configurations/{config_id}/refresh", response_model=ProductConfigurationResponse)
async def refresh_product_configuration(
    config_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    config = service.get_product_configuration(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    config = service.refresh_product_configuration(config)
    db.commit()
    return _config_to_response(config)


@config_router.post("/validate", response_model=Dict[str, Any])
async def validate_selections(
    request: ValidateSelectionsRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    ok, errors = service.validate_selections(
        request.product_item_id, request.selections
    )
    return {"ok": ok, "errors": errors}


@config_router.post("/effective-bom", response_model=Dict[str, Any])
async def effective_bom(
    request: EffectiveBomRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = ConfigService(db)
    return service.get_effective_bom(
        request.product_item_id,
        request.selections,
        levels=request.levels,
        effective_date=request.effective_date,
    )
