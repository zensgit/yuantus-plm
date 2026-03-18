"""Maintenance management service layer."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.maintenance.models import (
    Equipment,
    EquipmentStatus,
    MaintenanceCategory,
    MaintenanceRequest,
    MaintenanceRequestPriority,
    MaintenanceRequestState,
    MaintenanceType,
)


class MaintenanceService:
    """CRUD + domain logic for Equipment and Maintenance Requests."""

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def create_category(
        self,
        *,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> MaintenanceCategory:
        cat = MaintenanceCategory(
            id=str(uuid.uuid4()),
            name=name,
            parent_id=parent_id,
            description=description,
        )
        self.session.add(cat)
        self.session.flush()
        return cat

    def list_categories(self) -> List[MaintenanceCategory]:
        return (
            self.session.query(MaintenanceCategory)
            .order_by(MaintenanceCategory.name)
            .all()
        )

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------

    def create_equipment(
        self,
        *,
        name: str,
        serial_number: Optional[str] = None,
        model: Optional[str] = None,
        manufacturer: Optional[str] = None,
        category_id: Optional[str] = None,
        location: Optional[str] = None,
        plant_code: Optional[str] = None,
        workcenter_id: Optional[str] = None,
        owner_user_id: Optional[int] = None,
        team_name: Optional[str] = None,
        expected_mtbf_days: Optional[float] = None,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Equipment:
        equip = Equipment(
            id=str(uuid.uuid4()),
            name=name,
            serial_number=serial_number,
            model=model,
            manufacturer=manufacturer,
            category_id=category_id,
            status=EquipmentStatus.OPERATIONAL.value,
            location=location,
            plant_code=plant_code,
            workcenter_id=workcenter_id,
            owner_user_id=owner_user_id,
            team_name=team_name,
            expected_mtbf_days=expected_mtbf_days,
            properties=properties or {},
            created_by_id=user_id,
        )
        self.session.add(equip)
        self.session.flush()
        return equip

    def get_equipment(self, equipment_id: str) -> Optional[Equipment]:
        return self.session.get(Equipment, equipment_id)

    def list_equipment(
        self,
        *,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
        plant_code: Optional[str] = None,
    ) -> List[Equipment]:
        q = self.session.query(Equipment)
        if status is not None:
            q = q.filter(Equipment.status == status)
        if category_id is not None:
            q = q.filter(Equipment.category_id == category_id)
        if plant_code is not None:
            q = q.filter(Equipment.plant_code == plant_code)
        return q.order_by(Equipment.name).all()

    def update_equipment_status(
        self, equipment_id: str, *, status: str
    ) -> Equipment:
        equip = self.get_equipment(equipment_id)
        if not equip:
            raise ValueError(f"Equipment {equipment_id} not found")
        if status not in {e.value for e in EquipmentStatus}:
            raise ValueError(f"Invalid status: {status}")
        equip.status = status
        self.session.flush()
        return equip

    # ------------------------------------------------------------------
    # Maintenance Requests
    # ------------------------------------------------------------------

    def create_request(
        self,
        *,
        name: str,
        equipment_id: str,
        maintenance_type: str = MaintenanceType.CORRECTIVE.value,
        priority: str = MaintenanceRequestPriority.MEDIUM.value,
        description: Optional[str] = None,
        scheduled_date: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        duration_hours: Optional[float] = None,
        assigned_user_id: Optional[int] = None,
        team_name: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> MaintenanceRequest:
        if maintenance_type not in {e.value for e in MaintenanceType}:
            raise ValueError(f"Invalid maintenance_type: {maintenance_type}")
        if priority not in {e.value for e in MaintenanceRequestPriority}:
            raise ValueError(f"Invalid priority: {priority}")

        req = MaintenanceRequest(
            id=str(uuid.uuid4()),
            name=name,
            equipment_id=equipment_id,
            maintenance_type=maintenance_type,
            state=MaintenanceRequestState.DRAFT.value,
            priority=priority,
            description=description,
            scheduled_date=scheduled_date,
            due_date=due_date,
            duration_hours=duration_hours,
            assigned_user_id=assigned_user_id,
            team_name=team_name,
            created_by_id=user_id,
        )
        self.session.add(req)
        self.session.flush()
        return req

    def transition_request(
        self,
        request_id: str,
        *,
        target_state: str,
        resolution_note: Optional[str] = None,
    ) -> MaintenanceRequest:
        req = self.session.get(MaintenanceRequest, request_id)
        if not req:
            raise ValueError(f"MaintenanceRequest {request_id} not found")
        if target_state not in {e.value for e in MaintenanceRequestState}:
            raise ValueError(f"Invalid state: {target_state}")

        ALLOWED = {
            MaintenanceRequestState.DRAFT.value: {
                MaintenanceRequestState.SUBMITTED.value,
                MaintenanceRequestState.CANCELLED.value,
            },
            MaintenanceRequestState.SUBMITTED.value: {
                MaintenanceRequestState.IN_PROGRESS.value,
                MaintenanceRequestState.CANCELLED.value,
            },
            MaintenanceRequestState.IN_PROGRESS.value: {
                MaintenanceRequestState.DONE.value,
                MaintenanceRequestState.CANCELLED.value,
            },
            MaintenanceRequestState.DONE.value: set(),
            MaintenanceRequestState.CANCELLED.value: set(),
        }

        allowed = ALLOWED.get(req.state, set())
        if target_state not in allowed:
            raise ValueError(
                f"Cannot transition from {req.state} to {target_state}"
            )

        now = datetime.utcnow()
        req.state = target_state
        if target_state == MaintenanceRequestState.IN_PROGRESS.value:
            req.started_at = now
        elif target_state == MaintenanceRequestState.DONE.value:
            req.completed_at = now
            if resolution_note:
                req.resolution_note = resolution_note
        elif target_state == MaintenanceRequestState.CANCELLED.value:
            req.cancelled_at = now

        self.session.flush()
        return req

    def get_request(self, request_id: str) -> Optional[MaintenanceRequest]:
        return self.session.get(MaintenanceRequest, request_id)

    def list_requests(
        self,
        *,
        equipment_id: Optional[str] = None,
        state: Optional[str] = None,
        maintenance_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[MaintenanceRequest]:
        q = self.session.query(MaintenanceRequest)
        if equipment_id is not None:
            q = q.filter(MaintenanceRequest.equipment_id == equipment_id)
        if state is not None:
            q = q.filter(MaintenanceRequest.state == state)
        if maintenance_type is not None:
            q = q.filter(MaintenanceRequest.maintenance_type == maintenance_type)
        if priority is not None:
            q = q.filter(MaintenanceRequest.priority == priority)
        return q.order_by(MaintenanceRequest.created_at.desc()).all()

    # ------------------------------------------------------------------
    # C9 – Workcenter Readiness & Queue
    # ------------------------------------------------------------------

    def get_equipment_readiness_summary(
        self,
        *,
        plant_code: Optional[str] = None,
        workcenter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate equipment health snapshot.

        Returns counts by status and a list of equipment items that are
        *not* operational (i.e. need attention).
        """
        equipment = self.list_equipment(plant_code=plant_code)
        if workcenter_id is not None:
            equipment = [e for e in equipment if e.workcenter_id == workcenter_id]

        counts: Dict[str, int] = {}
        needs_attention: List[Dict[str, Any]] = []
        for e in equipment:
            counts[e.status] = counts.get(e.status, 0) + 1
            if e.status != EquipmentStatus.OPERATIONAL.value:
                needs_attention.append({
                    "equipment_id": e.id,
                    "name": e.name,
                    "status": e.status,
                    "workcenter_id": e.workcenter_id,
                    "plant_code": e.plant_code,
                })

        total = len(equipment)
        operational = counts.get(EquipmentStatus.OPERATIONAL.value, 0)
        return {
            "total_equipment": total,
            "operational": operational,
            "readiness_pct": round(operational / total * 100, 1) if total else 0.0,
            "status_counts": counts,
            "needs_attention": needs_attention,
            "filters": {
                "plant_code": plant_code,
                "workcenter_id": workcenter_id,
            },
        }

    def get_preventive_schedule(
        self,
        *,
        reference_date: Optional[datetime] = None,
        window_days: int = 30,
        include_overdue: bool = True,
    ) -> Dict[str, Any]:
        """Identify overdue and upcoming preventive maintenance requests.

        *Overdue* = preventive requests whose ``due_date`` < reference_date
        and state is not done/cancelled.

        *Upcoming* = preventive requests whose ``due_date`` falls within
        the next ``window_days`` from reference_date.
        """
        now = reference_date or datetime.utcnow()
        from datetime import timedelta

        window_end = now + timedelta(days=window_days)

        preventive_requests = self.list_requests(
            maintenance_type=MaintenanceType.PREVENTIVE.value,
        )

        active_states = {
            MaintenanceRequestState.DRAFT.value,
            MaintenanceRequestState.SUBMITTED.value,
            MaintenanceRequestState.IN_PROGRESS.value,
        }

        overdue: List[Dict[str, Any]] = []
        upcoming: List[Dict[str, Any]] = []

        for req in preventive_requests:
            if req.state not in active_states:
                continue
            if req.due_date is None:
                continue

            due = req.due_date
            # Strip timezone for comparison if reference_date is naive
            if due.tzinfo is not None and now.tzinfo is None:
                due = due.replace(tzinfo=None)

            entry = {
                "request_id": req.id,
                "name": req.name,
                "equipment_id": req.equipment_id,
                "state": req.state,
                "priority": req.priority,
                "due_date": req.due_date.isoformat() if req.due_date else None,
                "scheduled_date": req.scheduled_date.isoformat() if req.scheduled_date else None,
            }

            if include_overdue and due < now:
                days_overdue = (now - due).days
                entry["days_overdue"] = days_overdue
                overdue.append(entry)
            elif due <= window_end:
                days_until = (due - now).days
                entry["days_until_due"] = days_until
                upcoming.append(entry)

        return {
            "reference_date": now.isoformat(),
            "window_days": window_days,
            "overdue": overdue,
            "overdue_count": len(overdue),
            "upcoming": upcoming,
            "upcoming_count": len(upcoming),
        }

    def get_maintenance_queue_summary(
        self,
        *,
        plant_code: Optional[str] = None,
        workcenter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build an exportable maintenance work queue.

        Includes all non-terminal requests (draft, submitted, in_progress)
        with equipment context and priority breakdown.
        """
        active_states = {
            MaintenanceRequestState.DRAFT.value,
            MaintenanceRequestState.SUBMITTED.value,
            MaintenanceRequestState.IN_PROGRESS.value,
        }

        all_requests = self.list_requests()
        active_requests = [r for r in all_requests if r.state in active_states]

        # Filter by plant/workcenter via equipment lookup
        if plant_code is not None or workcenter_id is not None:
            equipment_map: Dict[str, Equipment] = {}
            for req in active_requests:
                if req.equipment_id not in equipment_map:
                    equip = self.get_equipment(req.equipment_id)
                    if equip:
                        equipment_map[req.equipment_id] = equip
            filtered = []
            for req in active_requests:
                equip = equipment_map.get(req.equipment_id)
                if not equip:
                    continue
                if plant_code is not None and equip.plant_code != plant_code:
                    continue
                if workcenter_id is not None and equip.workcenter_id != workcenter_id:
                    continue
                filtered.append(req)
            active_requests = filtered

        # Build queue items
        PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        queue_items: List[Dict[str, Any]] = []
        by_priority: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_state: Dict[str, int] = {}

        for req in active_requests:
            queue_items.append({
                "request_id": req.id,
                "name": req.name,
                "equipment_id": req.equipment_id,
                "maintenance_type": req.maintenance_type,
                "state": req.state,
                "priority": req.priority,
                "due_date": req.due_date.isoformat() if req.due_date else None,
                "scheduled_date": req.scheduled_date.isoformat() if req.scheduled_date else None,
                "team_name": req.team_name,
                "duration_hours": req.duration_hours,
            })
            by_priority[req.priority] = by_priority.get(req.priority, 0) + 1
            by_type[req.maintenance_type] = by_type.get(req.maintenance_type, 0) + 1
            by_state[req.state] = by_state.get(req.state, 0) + 1

        # Sort by priority then state
        queue_items.sort(key=lambda r: (PRIORITY_ORDER.get(r["priority"], 9), r["state"]))

        return {
            "total_active": len(queue_items),
            "by_priority": by_priority,
            "by_type": by_type,
            "by_state": by_state,
            "queue": queue_items,
            "filters": {
                "plant_code": plant_code,
                "workcenter_id": workcenter_id,
            },
        }
