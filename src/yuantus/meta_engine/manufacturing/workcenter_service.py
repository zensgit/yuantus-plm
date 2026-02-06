"""
WorkCenter service (resource center master data management).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from yuantus.meta_engine.manufacturing.models import WorkCenter


class WorkCenterService:
    def __init__(self, session: Session):
        self.session = session

    def list_workcenters(
        self,
        *,
        plant_code: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[WorkCenter]:
        query = self.session.query(WorkCenter)
        if plant_code:
            query = query.filter(WorkCenter.plant_code == plant_code)
        if not include_inactive:
            query = query.filter(WorkCenter.is_active.is_(True))
        return query.order_by(WorkCenter.code.asc()).all()

    def get_workcenter(self, workcenter_id: str) -> Optional[WorkCenter]:
        return self.session.get(WorkCenter, workcenter_id)

    def get_workcenter_by_code(self, code: str) -> Optional[WorkCenter]:
        return (
            self.session.query(WorkCenter)
            .filter(WorkCenter.code == code)
            .first()
        )

    def create_workcenter(self, payload: Dict[str, Any]) -> WorkCenter:
        code = (payload.get("code") or "").strip()
        name = (payload.get("name") or "").strip()
        if not code:
            raise ValueError("WorkCenter code is required")
        if not name:
            raise ValueError("WorkCenter name is required")

        if self.get_workcenter_by_code(code):
            raise ValueError(f"WorkCenter code already exists: {code}")

        workcenter = WorkCenter(
            id=payload.get("id") or str(uuid.uuid4()),
            code=code,
            name=name,
            description=payload.get("description"),
            plant_code=payload.get("plant_code"),
            department_code=payload.get("department_code"),
            capacity_per_day=float(payload.get("capacity_per_day", 8.0) or 8.0),
            efficiency=float(payload.get("efficiency", 1.0) or 1.0),
            utilization=float(payload.get("utilization", 0.9) or 0.9),
            machine_count=int(payload.get("machine_count", 1) or 1),
            worker_count=int(payload.get("worker_count", 1) or 1),
            cost_center=payload.get("cost_center"),
            labor_rate=payload.get("labor_rate"),
            overhead_rate=payload.get("overhead_rate"),
            scheduling_type=(payload.get("scheduling_type") or "finite").strip() or "finite",
            queue_time_default=float(payload.get("queue_time_default", 0.0) or 0.0),
            is_active=bool(payload.get("is_active", True)),
        )
        self.session.add(workcenter)
        self.session.flush()
        return workcenter

    def update_workcenter(
        self,
        workcenter: WorkCenter,
        payload: Dict[str, Any],
    ) -> WorkCenter:
        if "code" in payload and payload.get("code"):
            code = payload["code"].strip()
            if code != workcenter.code:
                existing = self.get_workcenter_by_code(code)
                if existing and existing.id != workcenter.id:
                    raise ValueError(f"WorkCenter code already exists: {code}")
                workcenter.code = code
        if "name" in payload and payload.get("name"):
            workcenter.name = payload["name"].strip()
        if "description" in payload:
            workcenter.description = payload.get("description")
        if "plant_code" in payload:
            workcenter.plant_code = payload.get("plant_code")
        if "department_code" in payload:
            workcenter.department_code = payload.get("department_code")
        if "capacity_per_day" in payload:
            workcenter.capacity_per_day = float(payload.get("capacity_per_day") or 8.0)
        if "efficiency" in payload:
            workcenter.efficiency = float(payload.get("efficiency") or 1.0)
        if "utilization" in payload:
            workcenter.utilization = float(payload.get("utilization") or 0.9)
        if "machine_count" in payload:
            workcenter.machine_count = int(payload.get("machine_count") or 1)
        if "worker_count" in payload:
            workcenter.worker_count = int(payload.get("worker_count") or 1)
        if "cost_center" in payload:
            workcenter.cost_center = payload.get("cost_center")
        if "labor_rate" in payload:
            workcenter.labor_rate = payload.get("labor_rate")
        if "overhead_rate" in payload:
            workcenter.overhead_rate = payload.get("overhead_rate")
        if "scheduling_type" in payload:
            workcenter.scheduling_type = (
                payload.get("scheduling_type") or "finite"
            ).strip() or "finite"
        if "queue_time_default" in payload:
            workcenter.queue_time_default = float(payload.get("queue_time_default") or 0.0)
        if "is_active" in payload:
            workcenter.is_active = bool(payload.get("is_active"))

        self.session.add(workcenter)
        self.session.flush()
        return workcenter
