from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.manufacturing.mbom_service import MBOMService
from yuantus.meta_engine.manufacturing.routing_service import RoutingService
from yuantus.meta_engine.manufacturing.workcenter_service import WorkCenterService
from yuantus.meta_engine.manufacturing.models import ManufacturingBOM, Routing, WorkCenter

mbom_router = APIRouter(prefix="/mboms", tags=["MBOM"])
routing_router = APIRouter(prefix="/routings", tags=["Routing"])
workcenter_router = APIRouter(prefix="/workcenters", tags=["WorkCenter"])


class MBOMCreateRequest(BaseModel):
    source_item_id: str
    name: str
    version: str = "1.0"
    plant_code: Optional[str] = None
    effective_from: Optional[datetime] = None
    transformation_rules: Optional[Dict[str, Any]] = None


class MBOMResponse(BaseModel):
    id: str
    source_item_id: str
    name: str
    version: str
    bom_type: Optional[str] = None
    plant_code: Optional[str] = None
    effective_from: Optional[datetime] = None
    state: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    structure: Optional[Dict[str, Any]] = None


class MBOMCompareRequest(BaseModel):
    ebom_item_id: str
    mbom_id: str


class RoutingCreateRequest(BaseModel):
    name: str
    mbom_id: Optional[str] = None
    item_id: Optional[str] = None
    routing_code: Optional[str] = None
    version: str = "1.0"
    is_primary: bool = True
    plant_code: Optional[str] = None


class RoutingResponse(BaseModel):
    id: str
    name: str
    mbom_id: Optional[str] = None
    item_id: Optional[str] = None
    routing_code: Optional[str] = None
    version: str
    is_primary: bool
    state: Optional[str] = None
    total_setup_time: float = 0.0
    total_run_time: float = 0.0
    total_labor_time: float = 0.0
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None


class OperationCreateRequest(BaseModel):
    operation_number: str
    name: str
    operation_type: str = "fabrication"
    workcenter_code: Optional[str] = None
    setup_time: float = 0.0
    run_time: float = 0.0
    labor_setup_time: Optional[float] = None
    labor_run_time: Optional[float] = None
    crew_size: int = 1
    is_subcontracted: bool = False
    inspection_required: bool = False
    work_instructions: Optional[str] = None
    sequence: Optional[int] = None


class OperationResponse(BaseModel):
    id: str
    routing_id: str
    operation_number: str
    name: str
    operation_type: str
    sequence: int
    setup_time: float
    run_time: float
    labor_setup_time: float
    labor_run_time: float


class TimeCalcRequest(BaseModel):
    quantity: int = Field(..., gt=0)
    include_queue: bool = True
    include_move: bool = True


class CostCalcRequest(BaseModel):
    quantity: int = Field(..., gt=0)
    labor_rate: Optional[float] = None
    overhead_rate: Optional[float] = None


class WorkCenterCreateRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    plant_code: Optional[str] = None
    department_code: Optional[str] = None
    capacity_per_day: float = 8.0
    efficiency: float = 1.0
    utilization: float = 0.9
    machine_count: int = 1
    worker_count: int = 1
    cost_center: Optional[str] = None
    labor_rate: Optional[float] = None
    overhead_rate: Optional[float] = None
    scheduling_type: str = "finite"
    queue_time_default: float = 0.0
    is_active: bool = True


class WorkCenterUpdateRequest(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    plant_code: Optional[str] = None
    department_code: Optional[str] = None
    capacity_per_day: Optional[float] = None
    efficiency: Optional[float] = None
    utilization: Optional[float] = None
    machine_count: Optional[int] = None
    worker_count: Optional[int] = None
    cost_center: Optional[str] = None
    labor_rate: Optional[float] = None
    overhead_rate: Optional[float] = None
    scheduling_type: Optional[str] = None
    queue_time_default: Optional[float] = None
    is_active: Optional[bool] = None


class WorkCenterResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    plant_code: Optional[str] = None
    department_code: Optional[str] = None
    capacity_per_day: float = 8.0
    efficiency: float = 1.0
    utilization: float = 0.9
    machine_count: int = 1
    worker_count: int = 1
    cost_center: Optional[str] = None
    labor_rate: Optional[float] = None
    overhead_rate: Optional[float] = None
    scheduling_type: str = "finite"
    queue_time_default: float = 0.0
    is_active: bool = True
    created_at: Optional[datetime] = None


def _ensure_admin(user: CurrentUser) -> None:
    roles = {str(role).lower() for role in (getattr(user, "roles", []) or [])}
    if bool(getattr(user, "is_superuser", False)):
        return
    if "admin" in roles or "superuser" in roles:
        return
    raise HTTPException(status_code=403, detail="Admin role required")


def _mbom_to_response(mbom: ManufacturingBOM, *, include_structure: bool) -> MBOMResponse:
    return MBOMResponse(
        id=mbom.id,
        source_item_id=mbom.source_item_id,
        name=mbom.name,
        version=mbom.version or "1.0",
        bom_type=mbom.bom_type,
        plant_code=mbom.plant_code,
        effective_from=mbom.effective_from,
        state=mbom.state,
        created_by_id=mbom.created_by_id,
        created_at=mbom.created_at,
        structure=mbom.structure if include_structure else None,
    )


def _routing_to_response(routing: Routing) -> RoutingResponse:
    return RoutingResponse(
        id=routing.id,
        name=routing.name,
        mbom_id=routing.mbom_id,
        item_id=routing.item_id,
        routing_code=routing.routing_code,
        version=routing.version or "1.0",
        is_primary=bool(routing.is_primary),
        state=routing.state,
        total_setup_time=routing.total_setup_time or 0.0,
        total_run_time=routing.total_run_time or 0.0,
        total_labor_time=routing.total_labor_time or 0.0,
        created_by_id=routing.created_by_id,
        created_at=routing.created_at,
    )


def _workcenter_to_response(workcenter: WorkCenter) -> WorkCenterResponse:
    return WorkCenterResponse(
        id=workcenter.id,
        code=workcenter.code,
        name=workcenter.name,
        description=workcenter.description,
        plant_code=workcenter.plant_code,
        department_code=workcenter.department_code,
        capacity_per_day=workcenter.capacity_per_day or 8.0,
        efficiency=workcenter.efficiency or 1.0,
        utilization=workcenter.utilization or 0.9,
        machine_count=workcenter.machine_count or 1,
        worker_count=workcenter.worker_count or 1,
        cost_center=workcenter.cost_center,
        labor_rate=workcenter.labor_rate,
        overhead_rate=workcenter.overhead_rate,
        scheduling_type=workcenter.scheduling_type or "finite",
        queue_time_default=workcenter.queue_time_default or 0.0,
        is_active=bool(workcenter.is_active),
        created_at=workcenter.created_at,
    )


@mbom_router.post("/from-ebom", response_model=MBOMResponse)
async def create_mbom_from_ebom(
    request: MBOMCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = MBOMService(db)
    try:
        mbom = service.create_mbom_from_ebom(
            request.source_item_id,
            request.name,
            version=request.version,
            plant_code=request.plant_code,
            effective_from=request.effective_from,
            user_id=int(user.id),
            transformation_rules=request.transformation_rules,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _mbom_to_response(mbom, include_structure=True)


@mbom_router.get("", response_model=List[MBOMResponse])
async def list_mboms(
    source_item_id: Optional[str] = Query(None),
    include_structure: bool = Query(False),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    q = db.query(ManufacturingBOM)
    if source_item_id:
        q = q.filter(ManufacturingBOM.source_item_id == source_item_id)
    items = q.order_by(ManufacturingBOM.created_at.desc()).all()
    return [_mbom_to_response(item, include_structure=include_structure) for item in items]


@mbom_router.get("/{mbom_id}", response_model=Dict[str, Any])
async def get_mbom(
    mbom_id: str,
    include_operations: bool = Query(False),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = MBOMService(db)
    try:
        structure = service.get_mbom_structure(mbom_id, include_operations=include_operations)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return structure


@mbom_router.post("/compare", response_model=Dict[str, Any])
async def compare_ebom_mbom(
    request: MBOMCompareRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = MBOMService(db)
    return service.compare_ebom_mbom(request.ebom_item_id, request.mbom_id)


@routing_router.post("", response_model=RoutingResponse)
async def create_routing(
    request: RoutingCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = RoutingService(db)
    try:
        routing = service.create_routing(
            request.name,
            mbom_id=request.mbom_id,
            item_id=request.item_id,
            routing_code=request.routing_code,
            version=request.version,
            is_primary=request.is_primary,
            plant_code=request.plant_code,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _routing_to_response(routing)


@routing_router.get("/{routing_id}", response_model=RoutingResponse)
async def get_routing(
    routing_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    routing = db.get(Routing, routing_id)
    if not routing:
        raise HTTPException(status_code=404, detail="Routing not found")
    return _routing_to_response(routing)


@routing_router.post("/{routing_id}/operations", response_model=OperationResponse)
async def add_operation(
    routing_id: str,
    request: OperationCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = RoutingService(db)
    try:
        op = service.add_operation(
            routing_id,
            request.operation_number,
            request.name,
            operation_type=request.operation_type,
            workcenter_code=request.workcenter_code,
            setup_time=request.setup_time,
            run_time=request.run_time,
            labor_setup_time=request.labor_setup_time,
            labor_run_time=request.labor_run_time,
            crew_size=request.crew_size,
            is_subcontracted=request.is_subcontracted,
            inspection_required=request.inspection_required,
            work_instructions=request.work_instructions,
            sequence=request.sequence,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OperationResponse(
        id=op.id,
        routing_id=op.routing_id,
        operation_number=op.operation_number,
        name=op.name,
        operation_type=op.operation_type,
        sequence=op.sequence,
        setup_time=op.setup_time or 0.0,
        run_time=op.run_time or 0.0,
        labor_setup_time=op.labor_setup_time or 0.0,
        labor_run_time=op.labor_run_time or 0.0,
    )


@routing_router.post("/{routing_id}/calculate-time", response_model=Dict[str, Any])
async def calculate_time(
    routing_id: str,
    request: TimeCalcRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = RoutingService(db)
    return service.calculate_production_time(
        routing_id,
        request.quantity,
        include_queue=request.include_queue,
        include_move=request.include_move,
    )


@routing_router.post("/{routing_id}/calculate-cost", response_model=Dict[str, Any])
async def calculate_cost(
    routing_id: str,
    request: CostCalcRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = RoutingService(db)
    return service.calculate_cost_estimate(
        routing_id,
        request.quantity,
        labor_rate=request.labor_rate,
        overhead_rate=request.overhead_rate,
    )


@routing_router.post("/{routing_id}/copy", response_model=RoutingResponse)
async def copy_routing(
    routing_id: str,
    new_name: str = Query(...),
    new_mbom_id: Optional[str] = Query(None),
    new_item_id: Optional[str] = Query(None),
    new_version: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = RoutingService(db)
    try:
        routing = service.copy_routing(
            routing_id,
            new_name,
            new_mbom_id=new_mbom_id,
            new_item_id=new_item_id,
            new_version=new_version,
            user_id=int(user.id),
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _routing_to_response(routing)


@workcenter_router.post("", response_model=WorkCenterResponse)
async def create_workcenter(
    request: WorkCenterCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_admin(user)
    service = WorkCenterService(db)
    try:
        workcenter = service.create_workcenter(request.model_dump())
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _workcenter_to_response(workcenter)


@workcenter_router.get("", response_model=List[WorkCenterResponse])
async def list_workcenters(
    plant_code: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkCenterService(db)
    items = service.list_workcenters(
        plant_code=plant_code,
        include_inactive=include_inactive,
    )
    return [_workcenter_to_response(item) for item in items]


@workcenter_router.get("/{workcenter_id}", response_model=WorkCenterResponse)
async def get_workcenter(
    workcenter_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    service = WorkCenterService(db)
    item = service.get_workcenter(workcenter_id)
    if not item:
        raise HTTPException(status_code=404, detail="WorkCenter not found")
    return _workcenter_to_response(item)


@workcenter_router.patch("/{workcenter_id}", response_model=WorkCenterResponse)
async def update_workcenter(
    workcenter_id: str,
    request: WorkCenterUpdateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    _ensure_admin(user)
    service = WorkCenterService(db)
    item = service.get_workcenter(workcenter_id)
    if not item:
        raise HTTPException(status_code=404, detail="WorkCenter not found")
    try:
        item = service.update_workcenter(item, request.model_dump(exclude_unset=True))
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _workcenter_to_response(item)
