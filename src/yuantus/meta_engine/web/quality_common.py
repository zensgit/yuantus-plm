"""Shared quality router models and serializers."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class QualityPointCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    check_type: str = "pass_fail"
    product_id: Optional[str] = None
    item_type_id: Optional[str] = None
    routing_id: Optional[str] = None
    operation_id: Optional[str] = None
    trigger_on: str = "manual"
    measure_min: Optional[float] = None
    measure_max: Optional[float] = None
    measure_unit: Optional[str] = None
    measure_tolerance: Optional[float] = None
    worksheet_template: Optional[str] = None
    instructions: Optional[str] = None
    team_name: Optional[str] = None
    sequence: int = 10
    properties: Optional[Dict[str, Any]] = None


class QualityPointUpdateRequest(BaseModel):
    name: Optional[str] = None
    check_type: Optional[str] = None
    is_active: Optional[bool] = None
    routing_id: Optional[str] = None
    operation_id: Optional[str] = None
    measure_min: Optional[float] = None
    measure_max: Optional[float] = None
    measure_unit: Optional[str] = None
    instructions: Optional[str] = None
    sequence: Optional[int] = None


class QualityCheckCreateRequest(BaseModel):
    point_id: str
    product_id: Optional[str] = None
    source_document_ref: Optional[str] = None
    lot_serial: Optional[str] = None


class QualityCheckRecordRequest(BaseModel):
    result: str
    measure_value: Optional[float] = None
    picture_path: Optional[str] = None
    worksheet_data: Optional[Dict[str, Any]] = None
    note: Optional[str] = None


class QualityAlertCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    check_id: Optional[str] = None
    product_id: Optional[str] = None
    description: Optional[str] = None
    priority: str = "medium"
    team_name: Optional[str] = None


class QualityAlertTransitionRequest(BaseModel):
    target_state: str


def point_to_dict(point) -> dict:
    return {
        "id": point.id,
        "name": point.name,
        "check_type": point.check_type,
        "product_id": point.product_id,
        "item_type_id": point.item_type_id,
        "routing_id": point.routing_id,
        "operation_id": point.operation_id,
        "trigger_on": point.trigger_on,
        "measure_min": point.measure_min,
        "measure_max": point.measure_max,
        "measure_unit": point.measure_unit,
        "is_active": point.is_active,
        "sequence": point.sequence,
        "team_name": point.team_name,
        "created_at": point.created_at.isoformat() if point.created_at else None,
    }


def check_to_dict(check) -> dict:
    return {
        "id": check.id,
        "point_id": check.point_id,
        "product_id": check.product_id,
        "routing_id": check.routing_id,
        "operation_id": check.operation_id,
        "check_type": check.check_type,
        "result": check.result,
        "measure_value": check.measure_value,
        "note": check.note,
        "source_document_ref": check.source_document_ref,
        "lot_serial": check.lot_serial,
        "checked_at": check.checked_at.isoformat() if check.checked_at else None,
        "checked_by_id": check.checked_by_id,
        "created_at": check.created_at.isoformat() if check.created_at else None,
    }


def alert_to_dict(alert) -> dict:
    return {
        "id": alert.id,
        "name": alert.name,
        "check_id": alert.check_id,
        "product_id": alert.product_id,
        "state": alert.state,
        "priority": alert.priority,
        "description": alert.description,
        "root_cause": alert.root_cause,
        "corrective_action": alert.corrective_action,
        "team_name": alert.team_name,
        "assigned_user_id": alert.assigned_user_id,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "confirmed_at": alert.confirmed_at.isoformat() if alert.confirmed_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "closed_at": alert.closed_at.isoformat() if alert.closed_at else None,
    }
