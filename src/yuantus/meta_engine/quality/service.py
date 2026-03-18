"""Quality assurance service layer."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.quality.models import (
    QualityAlert,
    QualityAlertPriority,
    QualityAlertState,
    QualityCheck,
    QualityCheckResult,
    QualityCheckType,
    QualityPoint,
)


class QualityService:
    """CRUD + domain logic for Quality Control Points, Checks, and Alerts."""

    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Quality Points
    # ------------------------------------------------------------------

    def create_point(
        self,
        *,
        name: str,
        check_type: str = QualityCheckType.PASS_FAIL.value,
        product_id: Optional[str] = None,
        item_type_id: Optional[str] = None,
        operation_id: Optional[str] = None,
        trigger_on: str = "manual",
        measure_min: Optional[float] = None,
        measure_max: Optional[float] = None,
        measure_unit: Optional[str] = None,
        measure_tolerance: Optional[float] = None,
        worksheet_template: Optional[str] = None,
        instructions: Optional[str] = None,
        team_name: Optional[str] = None,
        responsible_user_id: Optional[int] = None,
        sequence: int = 10,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> QualityPoint:
        if check_type not in {e.value for e in QualityCheckType}:
            raise ValueError(f"Invalid check_type: {check_type}")
        if trigger_on not in {"manual", "receipt", "production", "transfer"}:
            raise ValueError(f"Invalid trigger_on: {trigger_on}")

        point = QualityPoint(
            id=str(uuid.uuid4()),
            name=name,
            check_type=check_type,
            product_id=product_id,
            item_type_id=item_type_id,
            operation_id=operation_id,
            trigger_on=trigger_on,
            measure_min=measure_min,
            measure_max=measure_max,
            measure_unit=measure_unit,
            measure_tolerance=measure_tolerance,
            worksheet_template=worksheet_template,
            instructions=instructions,
            team_name=team_name,
            responsible_user_id=responsible_user_id,
            sequence=sequence,
            properties=properties or {},
            created_by_id=user_id,
        )
        self.session.add(point)
        self.session.flush()
        return point

    def get_point(self, point_id: str) -> Optional[QualityPoint]:
        return self.session.get(QualityPoint, point_id)

    def list_points(
        self,
        *,
        product_id: Optional[str] = None,
        item_type_id: Optional[str] = None,
        check_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[QualityPoint]:
        q = self.session.query(QualityPoint)
        if product_id is not None:
            q = q.filter(QualityPoint.product_id == product_id)
        if item_type_id is not None:
            q = q.filter(QualityPoint.item_type_id == item_type_id)
        if check_type is not None:
            q = q.filter(QualityPoint.check_type == check_type)
        if is_active is not None:
            q = q.filter(QualityPoint.is_active == is_active)
        return q.order_by(QualityPoint.sequence).all()

    def update_point(
        self, point_id: str, **fields: Any
    ) -> Optional[QualityPoint]:
        point = self.get_point(point_id)
        if not point:
            return None
        for key, value in fields.items():
            if hasattr(point, key):
                setattr(point, key, value)
        self.session.flush()
        return point

    # ------------------------------------------------------------------
    # Quality Checks
    # ------------------------------------------------------------------

    def create_check(
        self,
        *,
        point_id: str,
        product_id: Optional[str] = None,
        source_document_ref: Optional[str] = None,
        lot_serial: Optional[str] = None,
    ) -> QualityCheck:
        point = self.get_point(point_id)
        if not point:
            raise ValueError(f"QualityPoint {point_id} not found")

        check = QualityCheck(
            id=str(uuid.uuid4()),
            point_id=point_id,
            product_id=product_id or point.product_id,
            check_type=point.check_type,
            result=QualityCheckResult.NONE.value,
            source_document_ref=source_document_ref,
            lot_serial=lot_serial,
        )
        self.session.add(check)
        self.session.flush()
        return check

    def record_check_result(
        self,
        check_id: str,
        *,
        result: str,
        measure_value: Optional[float] = None,
        picture_path: Optional[str] = None,
        worksheet_data: Optional[Dict[str, Any]] = None,
        note: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> QualityCheck:
        check = self.session.get(QualityCheck, check_id)
        if not check:
            raise ValueError(f"QualityCheck {check_id} not found")
        if result not in {e.value for e in QualityCheckResult}:
            raise ValueError(f"Invalid result: {result}")

        check.result = result
        check.checked_at = datetime.utcnow()
        check.checked_by_id = user_id

        if measure_value is not None:
            check.measure_value = measure_value
        if picture_path is not None:
            check.picture_path = picture_path
        if worksheet_data is not None:
            check.worksheet_data = worksheet_data
        if note is not None:
            check.note = note

        # Auto-evaluate measure checks
        if check.check_type == QualityCheckType.MEASURE.value and measure_value is not None:
            point = self.get_point(check.point_id)
            if point and point.measure_min is not None and point.measure_max is not None:
                if point.measure_min <= measure_value <= point.measure_max:
                    check.result = QualityCheckResult.PASS.value
                else:
                    check.result = QualityCheckResult.FAIL.value

        self.session.flush()
        return check

    def get_check(self, check_id: str) -> Optional[QualityCheck]:
        return self.session.get(QualityCheck, check_id)

    def list_checks(
        self,
        *,
        point_id: Optional[str] = None,
        product_id: Optional[str] = None,
        result: Optional[str] = None,
    ) -> List[QualityCheck]:
        q = self.session.query(QualityCheck)
        if point_id is not None:
            q = q.filter(QualityCheck.point_id == point_id)
        if product_id is not None:
            q = q.filter(QualityCheck.product_id == product_id)
        if result is not None:
            q = q.filter(QualityCheck.result == result)
        return q.order_by(QualityCheck.created_at.desc()).all()

    # ------------------------------------------------------------------
    # Quality Alerts
    # ------------------------------------------------------------------

    def create_alert(
        self,
        *,
        name: str,
        check_id: Optional[str] = None,
        product_id: Optional[str] = None,
        description: Optional[str] = None,
        priority: str = QualityAlertPriority.MEDIUM.value,
        team_name: Optional[str] = None,
        assigned_user_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> QualityAlert:
        if priority not in {e.value for e in QualityAlertPriority}:
            raise ValueError(f"Invalid priority: {priority}")

        alert = QualityAlert(
            id=str(uuid.uuid4()),
            name=name,
            check_id=check_id,
            product_id=product_id,
            state=QualityAlertState.NEW.value,
            description=description,
            priority=priority,
            team_name=team_name,
            assigned_user_id=assigned_user_id,
            created_by_id=user_id,
        )
        self.session.add(alert)
        self.session.flush()
        return alert

    def transition_alert(
        self,
        alert_id: str,
        *,
        target_state: str,
        user_id: Optional[int] = None,
    ) -> QualityAlert:
        alert = self.session.get(QualityAlert, alert_id)
        if not alert:
            raise ValueError(f"QualityAlert {alert_id} not found")
        if target_state not in {e.value for e in QualityAlertState}:
            raise ValueError(f"Invalid state: {target_state}")

        ALLOWED_TRANSITIONS = {
            QualityAlertState.NEW.value: {
                QualityAlertState.CONFIRMED.value,
                QualityAlertState.CLOSED.value,
            },
            QualityAlertState.CONFIRMED.value: {
                QualityAlertState.IN_PROGRESS.value,
                QualityAlertState.CLOSED.value,
            },
            QualityAlertState.IN_PROGRESS.value: {
                QualityAlertState.RESOLVED.value,
                QualityAlertState.CLOSED.value,
            },
            QualityAlertState.RESOLVED.value: {
                QualityAlertState.CLOSED.value,
                QualityAlertState.IN_PROGRESS.value,  # reopen
            },
            QualityAlertState.CLOSED.value: set(),
        }

        allowed = ALLOWED_TRANSITIONS.get(alert.state, set())
        if target_state not in allowed:
            raise ValueError(
                f"Cannot transition from {alert.state} to {target_state}"
            )

        now = datetime.utcnow()
        alert.state = target_state
        if target_state == QualityAlertState.CONFIRMED.value:
            alert.confirmed_at = now
        elif target_state == QualityAlertState.RESOLVED.value:
            alert.resolved_at = now
        elif target_state == QualityAlertState.CLOSED.value:
            alert.closed_at = now

        self.session.flush()
        return alert

    def get_alert(self, alert_id: str) -> Optional[QualityAlert]:
        return self.session.get(QualityAlert, alert_id)

    def list_alerts(
        self,
        *,
        state: Optional[str] = None,
        priority: Optional[str] = None,
        product_id: Optional[str] = None,
    ) -> List[QualityAlert]:
        q = self.session.query(QualityAlert)
        if state is not None:
            q = q.filter(QualityAlert.state == state)
        if priority is not None:
            q = q.filter(QualityAlert.priority == priority)
        if product_id is not None:
            q = q.filter(QualityAlert.product_id == product_id)
        return q.order_by(QualityAlert.created_at.desc()).all()
