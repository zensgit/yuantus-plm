"""
Routing service (operations + time/cost calculations).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from yuantus.meta_engine.manufacturing.models import Operation, Routing, WorkCenter


class RoutingService:
    def __init__(self, session: Session):
        self.session = session

    def _scope_filters(
        self,
        *,
        mbom_id: Optional[str] = None,
        item_id: Optional[str] = None,
    ):
        if mbom_id:
            return (Routing.mbom_id == mbom_id,)
        if item_id:
            return (Routing.item_id == item_id,)
        return ()

    def _clear_primary_in_scope(
        self,
        *,
        mbom_id: Optional[str] = None,
        item_id: Optional[str] = None,
        exclude_routing_id: Optional[str] = None,
    ) -> None:
        scope = self._scope_filters(mbom_id=mbom_id, item_id=item_id)
        if not scope:
            return
        query = self.session.query(Routing).filter(*scope)
        if exclude_routing_id:
            query = query.filter(Routing.id != exclude_routing_id)
        for routing in query.all():
            routing.is_primary = False
            self.session.add(routing)

    def _resolve_workcenter(
        self,
        *,
        workcenter_id: Optional[str] = None,
        workcenter_code: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        normalized_id = (workcenter_id or "").strip() or None
        normalized_code = (workcenter_code or "").strip() or None
        if not normalized_id and not normalized_code:
            return None, None

        workcenter = None
        if normalized_id:
            workcenter = self.session.get(WorkCenter, normalized_id)
            if not workcenter:
                raise ValueError(f"WorkCenter not found: {normalized_id}")
            if normalized_code and (workcenter.code or "") != normalized_code:
                raise ValueError(
                    f"WorkCenter id/code mismatch: id={normalized_id}, code={normalized_code}"
                )
        elif normalized_code:
            workcenter = (
                self.session.query(WorkCenter)
                .filter(WorkCenter.code == normalized_code)
                .first()
            )
            if not workcenter:
                raise ValueError(f"WorkCenter not found: {normalized_code}")

        if not bool(workcenter.is_active):
            raise ValueError(f"WorkCenter is inactive: {workcenter.code}")

        return workcenter.id, workcenter.code

    def create_routing(
        self,
        name: str,
        *,
        mbom_id: Optional[str] = None,
        item_id: Optional[str] = None,
        routing_code: Optional[str] = None,
        version: str = "1.0",
        is_primary: bool = True,
        plant_code: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Routing:
        if not mbom_id and not item_id:
            raise ValueError("Either mbom_id or item_id must be provided")

        routing = Routing(
            id=str(uuid.uuid4()),
            mbom_id=mbom_id,
            item_id=item_id,
            name=name,
            routing_code=routing_code or f"RTG-{uuid.uuid4().hex[:8].upper()}",
            version=version,
            is_primary=is_primary,
            plant_code=plant_code,
            created_by_id=user_id,
        )
        self.session.add(routing)
        self.session.flush()
        if bool(is_primary):
            self._clear_primary_in_scope(
                mbom_id=mbom_id,
                item_id=item_id,
                exclude_routing_id=routing.id,
            )
        return routing

    def list_routings(
        self,
        *,
        mbom_id: Optional[str] = None,
        item_id: Optional[str] = None,
    ):
        query = self.session.query(Routing)
        if mbom_id:
            query = query.filter(Routing.mbom_id == mbom_id)
        if item_id:
            query = query.filter(Routing.item_id == item_id)
        return query.order_by(Routing.created_at.desc()).all()

    def add_operation(
        self,
        routing_id: str,
        operation_number: str,
        name: str,
        *,
        operation_type: str = "fabrication",
        workcenter_id: Optional[str] = None,
        workcenter_code: Optional[str] = None,
        setup_time: float = 0.0,
        run_time: float = 0.0,
        labor_setup_time: Optional[float] = None,
        labor_run_time: Optional[float] = None,
        crew_size: int = 1,
        is_subcontracted: bool = False,
        inspection_required: bool = False,
        work_instructions: Optional[str] = None,
        sequence: Optional[int] = None,
    ) -> Operation:
        routing = self.session.get(Routing, routing_id)
        if not routing:
            raise ValueError(f"Routing not found: {routing_id}")
        resolved_workcenter_id, resolved_workcenter_code = self._resolve_workcenter(
            workcenter_id=workcenter_id,
            workcenter_code=workcenter_code,
        )

        if sequence is None:
            existing = (
                self.session.query(Operation)
                .filter(Operation.routing_id == routing_id)
                .count()
            )
            sequence = (existing + 1) * 10

        operation = Operation(
            id=str(uuid.uuid4()),
            routing_id=routing_id,
            operation_number=operation_number,
            name=name,
            operation_type=operation_type,
            sequence=sequence,
            workcenter_id=resolved_workcenter_id,
            workcenter_code=resolved_workcenter_code,
            setup_time=setup_time,
            run_time=run_time,
            labor_setup_time=labor_setup_time if labor_setup_time is not None else setup_time,
            labor_run_time=labor_run_time if labor_run_time is not None else run_time,
            crew_size=crew_size,
            is_subcontracted=is_subcontracted,
            inspection_required=inspection_required,
            work_instructions=work_instructions,
        )
        self.session.add(operation)
        self.session.flush()

        self._update_routing_totals(routing_id)
        return operation

    def _update_routing_totals(self, routing_id: str) -> None:
        routing = self.session.get(Routing, routing_id)
        if not routing:
            return

        operations = (
            self.session.query(Operation)
            .filter(Operation.routing_id == routing_id)
            .all()
        )

        routing.total_setup_time = sum(op.setup_time or 0 for op in operations)
        routing.total_run_time = sum(op.run_time or 0 for op in operations)
        routing.total_labor_time = sum(
            (op.labor_setup_time or 0) + (op.labor_run_time or 0)
            for op in operations
        )
        self.session.add(routing)

    def calculate_production_time(
        self,
        routing_id: str,
        quantity: int,
        *,
        include_queue: bool = True,
        include_move: bool = True,
    ) -> Dict[str, Any]:
        operations = (
            self.session.query(Operation)
            .filter(Operation.routing_id == routing_id)
            .order_by(Operation.sequence)
            .all()
        )

        result = {
            "total_time": 0.0,
            "setup_time": 0.0,
            "run_time": 0.0,
            "queue_time": 0.0,
            "move_time": 0.0,
            "labor_time": 0.0,
            "operations": [],
        }

        for op in operations:
            op_setup = op.setup_time or 0
            op_run = (op.run_time or 0) * quantity
            op_queue = (op.queue_time or 0) if include_queue else 0
            op_move = (op.move_time or 0) if include_move else 0
            op_labor = (op.labor_setup_time or 0) + (op.labor_run_time or 0) * quantity

            op_total = op_setup + op_run + op_queue + op_move

            result["operations"].append(
                {
                    "operation_id": op.id,
                    "operation_number": op.operation_number,
                    "name": op.name,
                    "setup_time": op_setup,
                    "run_time": op_run,
                    "queue_time": op_queue,
                    "move_time": op_move,
                    "labor_time": op_labor,
                    "total_time": op_total,
                }
            )

            result["setup_time"] += op_setup
            result["run_time"] += op_run
            result["queue_time"] += op_queue
            result["move_time"] += op_move
            result["labor_time"] += op_labor
            result["total_time"] += op_total

        return result

    def calculate_cost_estimate(
        self,
        routing_id: str,
        quantity: int,
        *,
        labor_rate: Optional[float] = None,
        overhead_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        time_calc = self.calculate_production_time(routing_id, quantity)

        operations = (
            self.session.query(Operation)
            .filter(Operation.routing_id == routing_id)
            .all()
        )

        labor_cost = 0.0
        overhead_cost = 0.0

        for op in operations:
            op_labor_rate = op.labor_cost_rate or labor_rate or 50.0
            op_overhead_rate = op.overhead_rate or overhead_rate or 30.0

            op_labor_time = (op.labor_setup_time or 0) + (op.labor_run_time or 0) * quantity
            op_labor_cost = op_labor_time / 60 * op_labor_rate

            op_run_time = (op.setup_time or 0) + (op.run_time or 0) * quantity
            op_overhead_cost = op_run_time / 60 * op_overhead_rate

            labor_cost += op_labor_cost
            overhead_cost += op_overhead_cost

        total = labor_cost + overhead_cost

        return {
            "quantity": quantity,
            "labor_cost": round(labor_cost, 2),
            "overhead_cost": round(overhead_cost, 2),
            "total_cost": round(total, 2),
            "cost_per_unit": round(total / quantity, 2) if quantity else 0,
            "time_summary": {
                "total_minutes": time_calc["total_time"],
                "total_hours": round(time_calc["total_time"] / 60, 2),
            },
        }

    def copy_routing(
        self,
        source_routing_id: str,
        new_name: str,
        *,
        new_mbom_id: Optional[str] = None,
        new_item_id: Optional[str] = None,
        new_version: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Routing:
        source = self.session.get(Routing, source_routing_id)
        if not source:
            raise ValueError(f"Source routing not found: {source_routing_id}")

        new_routing = Routing(
            id=str(uuid.uuid4()),
            mbom_id=new_mbom_id or source.mbom_id,
            item_id=new_item_id or source.item_id,
            name=new_name,
            routing_code=f"RTG-{uuid.uuid4().hex[:8].upper()}",
            version=new_version or source.version,
            is_primary=False,
            plant_code=source.plant_code,
            line_code=source.line_code,
            created_by_id=user_id,
        )
        self.session.add(new_routing)
        self.session.flush()

        source_ops = (
            self.session.query(Operation)
            .filter(Operation.routing_id == source_routing_id)
            .order_by(Operation.sequence)
            .all()
        )

        for op in source_ops:
            new_op = Operation(
                id=str(uuid.uuid4()),
                routing_id=new_routing.id,
                operation_number=op.operation_number,
                name=op.name,
                operation_type=op.operation_type,
                sequence=op.sequence,
                workcenter_id=op.workcenter_id,
                workcenter_code=op.workcenter_code,
                setup_time=op.setup_time,
                run_time=op.run_time,
                queue_time=op.queue_time,
                move_time=op.move_time,
                labor_setup_time=op.labor_setup_time,
                labor_run_time=op.labor_run_time,
                crew_size=op.crew_size,
                is_subcontracted=op.is_subcontracted,
                inspection_required=op.inspection_required,
                work_instructions=op.work_instructions,
                tooling_requirements=op.tooling_requirements,
                document_ids=op.document_ids,
            )
            self.session.add(new_op)

        self.session.flush()
        self._update_routing_totals(new_routing.id)
        return new_routing

    def set_primary_routing(self, routing_id: str) -> Routing:
        routing = self.session.get(Routing, routing_id)
        if not routing:
            raise ValueError(f"Routing not found: {routing_id}")

        scope = self._scope_filters(mbom_id=routing.mbom_id, item_id=routing.item_id)
        if not scope:
            raise ValueError(
                "Routing is missing scope (mbom_id/item_id); cannot set primary"
            )

        self._clear_primary_in_scope(
            mbom_id=routing.mbom_id,
            item_id=routing.item_id,
            exclude_routing_id=routing.id,
        )
        routing.is_primary = True
        self.session.add(routing)
        self.session.flush()
        return routing
