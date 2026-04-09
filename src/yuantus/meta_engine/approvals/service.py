"""Generic approvals service layer."""
from __future__ import annotations

import csv
import uuid
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.approvals.models import (
    ApprovalCategory,
    ApprovalPriority,
    ApprovalRequest,
    ApprovalRequestEvent,
    ApprovalRequestEventType,
    ApprovalState,
)


class ApprovalService:
    """CRUD + state machine for generic approval requests."""

    # State transition map
    _TRANSITIONS = {
        ApprovalState.DRAFT.value: {
            ApprovalState.PENDING.value,
            ApprovalState.CANCELLED.value,
        },
        ApprovalState.PENDING.value: {
            ApprovalState.APPROVED.value,
            ApprovalState.REJECTED.value,
            ApprovalState.CANCELLED.value,
        },
        ApprovalState.APPROVED.value: set(),
        ApprovalState.REJECTED.value: {
            ApprovalState.PENDING.value,  # allow resubmission
        },
        ApprovalState.CANCELLED.value: set(),
    }

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

    @staticmethod
    def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @classmethod
    def _age_hours(cls, value: Optional[datetime], now: Optional[datetime] = None) -> Optional[float]:
        normalized_value = cls._normalize_datetime(value)
        if normalized_value is None:
            return None
        normalized_now = cls._normalize_datetime(now or datetime.utcnow())
        if normalized_now is None:
            return None
        delta = normalized_now - normalized_value
        return round(delta.total_seconds() / 3600.0, 2)

    @staticmethod
    def _request_dict(req: ApprovalRequest) -> Dict[str, Any]:
        age_hours = ApprovalService._age_hours(req.created_at)
        return {
            "id": req.id,
            "title": req.title,
            "category_id": req.category_id,
            "entity_type": req.entity_type,
            "entity_id": req.entity_id,
            "state": req.state,
            "priority": req.priority,
            "description": req.description,
            "rejection_reason": req.rejection_reason,
            "requested_by_id": req.requested_by_id,
            "assigned_to_id": req.assigned_to_id,
            "decided_by_id": req.decided_by_id,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "submitted_at": req.submitted_at.isoformat() if req.submitted_at else None,
            "decided_at": req.decided_at.isoformat() if req.decided_at else None,
            "cancelled_at": req.cancelled_at.isoformat() if req.cancelled_at else None,
            "age_hours": age_hours,
            "properties": req.properties or {},
        }

    @classmethod
    def _build_request_milestones(cls, req: ApprovalRequest) -> List[Dict[str, Any]]:
        milestones: List[Dict[str, Any]] = []

        def append_milestone(
            event_type: str,
            *,
            at: Optional[datetime],
            state: Optional[str],
            actor_id: Optional[int] = None,
            note: Optional[str] = None,
        ) -> None:
            if at is None:
                return
            milestones.append(
                {
                    "event_type": event_type,
                    "state": state,
                    "at": at.isoformat(),
                    "actor_id": actor_id,
                    "note": note,
                }
            )

        append_milestone(
            "created",
            at=req.created_at,
            state=ApprovalState.DRAFT.value,
            actor_id=req.requested_by_id,
        )
        append_milestone(
            "submitted",
            at=req.submitted_at,
            state=ApprovalState.PENDING.value,
            actor_id=req.requested_by_id,
        )
        if req.decided_at is not None:
            decision_event = "approved"
            decision_state = ApprovalState.APPROVED.value
            decision_note = None
            if req.state == ApprovalState.REJECTED.value or req.rejection_reason:
                decision_event = "rejected"
                decision_state = ApprovalState.REJECTED.value
                decision_note = req.rejection_reason
            append_milestone(
                decision_event,
                at=req.decided_at,
                state=decision_state,
                actor_id=req.decided_by_id,
                note=decision_note,
            )
        append_milestone(
            "cancelled",
            at=req.cancelled_at,
            state=ApprovalState.CANCELLED.value,
            actor_id=req.decided_by_id,
        )
        milestones.sort(key=lambda row: row["at"])
        return milestones

    @classmethod
    def _request_status(cls, req: ApprovalRequest) -> Dict[str, Any]:
        milestones = cls._build_request_milestones(req)
        latest = milestones[-1] if milestones else None
        return {
            "is_terminal": req.state
            in {ApprovalState.APPROVED.value, ApprovalState.CANCELLED.value},
            "requires_decision": req.state == ApprovalState.PENDING.value,
            "can_resubmit": req.state == ApprovalState.REJECTED.value,
            "is_assigned": req.assigned_to_id is not None,
            "latest_event_type": latest["event_type"] if latest else None,
            "latest_event_at": latest["at"] if latest else None,
            "milestone_count": len(milestones),
        }

    @classmethod
    def _request_export_row(cls, req: ApprovalRequest) -> Dict[str, Any]:
        row = cls._request_dict(req)
        row.update(cls._request_status(req))
        return row

    @staticmethod
    def _normalize_export_format(fmt: str) -> str:
        normalized = (fmt or "").strip().lower()
        if normalized not in {"json", "csv", "markdown"}:
            raise ValueError(f"Unsupported format: {fmt}")
        return normalized

    @staticmethod
    def _event_row_dict(event: ApprovalRequestEvent) -> Dict[str, Any]:
        return {
            "id": event.id,
            "event_type": event.event_type,
            "transition_type": event.transition_type,
            "from_state": event.from_state,
            "to_state": event.to_state,
            "actor_id": event.actor_id,
            "note": event.note,
            "properties": event.properties or {},
            "at": event.created_at.isoformat() if event.created_at else None,
        }

    @classmethod
    def _build_request_history_events(cls, req: ApprovalRequest) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        previous_state: Optional[str] = None
        for milestone in cls._build_request_milestones(req):
            event_type = "created" if milestone["event_type"] == "created" else "transition"
            events.append(
                {
                    "event_type": event_type,
                    "transition_type": milestone["event_type"] if event_type == "transition" else None,
                    "from_state": previous_state,
                    "to_state": milestone["state"],
                    "actor_id": milestone["actor_id"],
                    "note": milestone["note"],
                    "at": milestone["at"],
                }
            )
            previous_state = milestone["state"]
        return events

    @classmethod
    def _build_request_milestones_from_events(
        cls,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "event_type": event.get("transition_type") or event["event_type"],
                "state": event["to_state"],
                "at": event["at"],
                "actor_id": event["actor_id"],
                "note": event["note"],
                "properties": event.get("properties") or {},
            }
            for event in events
        ]

    @classmethod
    def _latest_request_activity_at(cls, req: ApprovalRequest) -> Optional[str]:
        timestamps = [
            value.isoformat()
            for value in (
                req.created_at,
                req.submitted_at,
                req.decided_at,
                req.cancelled_at,
            )
            if value is not None
        ]
        return max(timestamps) if timestamps else None

    @staticmethod
    def _render_csv(rows: List[Dict[str, Any]], fieldnames: List[str]) -> str:
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name) for name in fieldnames})
        return buffer.getvalue()

    @staticmethod
    def _render_markdown_table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"
        body = [
            "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
            for row in rows
        ]
        return "\n".join([header, separator, *body]) if body else "\n".join([header, separator])

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def create_category(
        self,
        *,
        name: str,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ApprovalCategory:
        cat = ApprovalCategory(
            id=str(uuid.uuid4()),
            name=name,
            parent_id=parent_id,
            description=description,
        )
        self.session.add(cat)
        self.session.flush()
        return cat

    def list_categories(self) -> List[ApprovalCategory]:
        return (
            self.session.query(ApprovalCategory)
            .order_by(ApprovalCategory.name)
            .all()
        )

    # ------------------------------------------------------------------
    # Approval Requests
    # ------------------------------------------------------------------

    def create_request(
        self,
        *,
        title: str,
        category_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        priority: str = ApprovalPriority.NORMAL.value,
        description: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
        user_id: Optional[int] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        if priority not in {e.value for e in ApprovalPriority}:
            raise ValueError(f"Invalid priority: {priority}")

        now = datetime.utcnow()
        req = ApprovalRequest(
            id=str(uuid.uuid4()),
            title=title,
            category_id=category_id,
            entity_type=entity_type,
            entity_id=entity_id,
            state=ApprovalState.DRAFT.value,
            priority=priority,
            description=description,
            assigned_to_id=assigned_to_id,
            requested_by_id=user_id,
            properties=properties or {},
            created_at=now,
        )
        self.session.add(req)
        self.session.flush()
        self._create_request_event(
            request_id=req.id,
            event_type=ApprovalRequestEventType.CREATED.value,
            from_state=None,
            to_state=ApprovalState.DRAFT.value,
            transition_type=None,
            actor_id=user_id,
            note=None,
            properties={},
        )
        self.session.flush()
        return req

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self.session.get(ApprovalRequest, request_id)

    def list_request_events(self, request_id: str) -> List[ApprovalRequestEvent]:
        events = self.session.query(ApprovalRequestEvent).order_by(
            ApprovalRequestEvent.created_at.asc()
        )
        return [event for event in events.all() if event.request_id == request_id]

    def _request_status_with_history(self, req: ApprovalRequest) -> Dict[str, Any]:
        status = self._request_status(req)
        events = self.list_request_events(req.id)
        if events:
            latest_event = self._event_row_dict(events[-1])
            status.update(
                {
                    "latest_event_type": latest_event.get("transition_type")
                    or latest_event["event_type"],
                    "latest_event_at": latest_event["at"],
                    "milestone_count": len(events),
                }
            )
        return status

    def get_request_read_model(self, request_id: str) -> Dict[str, Any]:
        req = self.get_request(request_id)
        if not req:
            raise ValueError(f"ApprovalRequest {request_id} not found")
        payload = self._request_dict(req)
        payload["status"] = self._request_status_with_history(req)
        return payload

    def get_request_lifecycle(self, request_id: str) -> Dict[str, Any]:
        req = self.get_request(request_id)
        if not req:
            raise ValueError(f"ApprovalRequest {request_id} not found")
        events = [self._event_row_dict(event) for event in self.list_request_events(request_id)]
        milestones = (
            self._build_request_milestones_from_events(events)
            if events
            else self._build_request_milestones(req)
        )
        return {
            "request_id": req.id,
            "current_state": req.state,
            "milestone_count": len(milestones),
            "latest": milestones[-1] if milestones else None,
            "milestones": milestones,
            "generated_at": self._utcnow_iso(),
        }

    def get_request_consumer_summary(
        self,
        request_id: str,
        *,
        include_history: bool = False,
        history_limit: int = 5,
    ) -> Dict[str, Any]:
        req = self.get_request(request_id)
        if not req:
            raise ValueError(f"ApprovalRequest {request_id} not found")
        lifecycle = self.get_request_lifecycle(request_id)
        history = (
            self.get_request_history(request_id, limit=history_limit)
            if include_history
            else None
        )
        proof = {
            "assignment": {
                "requested_by_id": req.requested_by_id,
                "assigned_to_id": req.assigned_to_id,
                "decided_by_id": req.decided_by_id,
            },
            "lifecycle": {
                "latest": lifecycle["latest"],
                "milestone_count": lifecycle["milestone_count"],
                "milestones": lifecycle["milestones"],
            },
            "audit": {
                "enabled": include_history,
                "history_count": history["total"] if history else 0,
                "history_limit": history_limit if include_history else None,
                "latest": history["latest"] if history else None,
            },
            "transition_api": f"/api/v1/approvals/requests/{request_id}/transition",
            "history_api": f"/api/v1/approvals/requests/{request_id}/history",
            "allowed_transitions": sorted(self._TRANSITIONS.get(req.state, set())),
        }
        if history is not None:
            proof["history"] = history["events"]
        return {
            "request": self._request_dict(req),
            "status": self._request_status_with_history(req),
            "proof": proof,
            "generated_at": self._utcnow_iso(),
        }

    def get_request_history(
        self,
        request_id: str,
        *,
        limit: int = 5,
    ) -> Dict[str, Any]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        req = self.get_request(request_id)
        if not req:
            raise ValueError(f"ApprovalRequest {request_id} not found")
        stored_events = [self._event_row_dict(event) for event in self.list_request_events(request_id)]
        events = stored_events or self._build_request_history_events(req)
        return {
            "request_id": req.id,
            "current_state": req.state,
            "total": len(events),
            "latest": events[-1] if events else None,
            "events": events[-limit:],
            "generated_at": self._utcnow_iso(),
        }

    def get_request_pack_row(
        self,
        request_id: str,
        *,
        include_history: bool = False,
        history_limit: int = 5,
    ) -> Dict[str, Any]:
        req = self.get_request(request_id)
        if not req:
            return {
                "request_id": request_id,
                "found": False,
                "title": None,
                "state": "not_found",
                "priority": None,
                "entity_type": None,
                "entity_id": None,
                "assigned_to_id": None,
                "status": None,
                "proof": None,
            }
        summary = self.get_request_consumer_summary(
            request_id,
            include_history=include_history,
            history_limit=history_limit,
        )
        return {
            "request_id": req.id,
            "found": True,
            "title": req.title,
            "state": req.state,
            "priority": req.priority,
            "entity_type": req.entity_type,
            "entity_id": req.entity_id,
            "assigned_to_id": req.assigned_to_id,
            "age_hours": self._age_hours(req.created_at),
            "status": summary["status"],
            "proof": summary["proof"],
        }

    def list_requests(
        self,
        *,
        state: Optional[str] = None,
        category_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
    ) -> List[ApprovalRequest]:
        q = self.session.query(ApprovalRequest)
        if state is not None:
            q = q.filter(ApprovalRequest.state == state)
        if category_id is not None:
            q = q.filter(ApprovalRequest.category_id == category_id)
        if entity_type is not None:
            q = q.filter(ApprovalRequest.entity_type == entity_type)
        if entity_id is not None:
            q = q.filter(ApprovalRequest.entity_id == entity_id)
        if priority is not None:
            q = q.filter(ApprovalRequest.priority == priority)
        if assigned_to_id is not None:
            q = q.filter(ApprovalRequest.assigned_to_id == assigned_to_id)
        return q.order_by(ApprovalRequest.created_at.desc()).all()

    def transition_request(
        self,
        request_id: str,
        *,
        target_state: str,
        rejection_reason: Optional[str] = None,
        decided_by_id: Optional[int] = None,
    ) -> ApprovalRequest:
        req = self.session.get(ApprovalRequest, request_id)
        if not req:
            raise ValueError(f"ApprovalRequest {request_id} not found")
        if target_state not in {e.value for e in ApprovalState}:
            raise ValueError(f"Invalid state: {target_state}")

        allowed = self._TRANSITIONS.get(req.state, set())
        if target_state not in allowed:
            raise ValueError(
                f"Cannot transition from {req.state} to {target_state}"
            )

        now = datetime.utcnow()
        from_state = req.state
        req.state = target_state

        if target_state == ApprovalState.PENDING.value:
            req.submitted_at = now
            if from_state == ApprovalState.REJECTED.value:
                req.rejection_reason = None
                req.decided_at = None
                req.decided_by_id = None
        elif target_state == ApprovalState.APPROVED.value:
            req.decided_at = now
            req.decided_by_id = decided_by_id
        elif target_state == ApprovalState.REJECTED.value:
            req.decided_at = now
            req.decided_by_id = decided_by_id
            if rejection_reason:
                req.rejection_reason = rejection_reason
        elif target_state == ApprovalState.CANCELLED.value:
            req.cancelled_at = now

        self._create_request_event(
            request_id=req.id,
            event_type=ApprovalRequestEventType.TRANSITION.value,
            from_state=from_state,
            to_state=target_state,
            transition_type=self._transition_type_for_event(from_state, target_state),
            actor_id=decided_by_id,
            note=rejection_reason if target_state == ApprovalState.REJECTED.value else None,
            properties={},
        )
        self.session.flush()
        return req

    @staticmethod
    def _transition_type_for_event(from_state: str, target_state: str) -> str:
        if target_state == ApprovalState.PENDING.value:
            return "resubmitted" if from_state == ApprovalState.REJECTED.value else "submitted"
        if target_state == ApprovalState.APPROVED.value:
            return "approved"
        if target_state == ApprovalState.REJECTED.value:
            return "rejected"
        if target_state == ApprovalState.CANCELLED.value:
            return "cancelled"
        return "transition"

    def _create_request_event(
        self,
        *,
        request_id: str,
        event_type: str,
        from_state: Optional[str],
        to_state: str,
        transition_type: Optional[str],
        actor_id: Optional[int],
        note: Optional[str],
        properties: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequestEvent:
        event = ApprovalRequestEvent(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=event_type,
            transition_type=transition_type,
            from_state=from_state,
            to_state=to_state,
            actor_id=actor_id,
            note=note,
            properties=properties or {},
        )
        self.session.add(event)
        return event

    def get_summary(
        self,
        *,
        entity_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate approval status counts."""
        requests = self.list_requests(
            entity_type=entity_type,
            category_id=category_id,
        )
        by_state: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        for req in requests:
            by_state[req.state] = by_state.get(req.state, 0) + 1
            by_priority[req.priority] = by_priority.get(req.priority, 0) + 1

        pending = by_state.get(ApprovalState.PENDING.value, 0)
        terminal_count = sum(
            by_state.get(state, 0)
            for state in (
                ApprovalState.APPROVED.value,
                ApprovalState.CANCELLED.value,
            )
        )
        resubmittable_count = by_state.get(ApprovalState.REJECTED.value, 0)
        unassigned_pending_count = sum(
            1
            for req in requests
            if req.state == ApprovalState.PENDING.value and req.assigned_to_id is None
        )
        latest_activity_at = max(
            (
                self._latest_request_activity_at(req)
                for req in requests
                if self._latest_request_activity_at(req) is not None
            ),
            default=None,
        )
        return {
            "total": len(requests),
            "pending": pending,
            "terminal_count": terminal_count,
            "resubmittable_count": resubmittable_count,
            "unassigned_pending_count": unassigned_pending_count,
            "by_state": by_state,
            "by_priority": by_priority,
            "filters": {
                "entity_type": entity_type,
                "category_id": category_id,
            },
            "latest_activity_at": latest_activity_at,
            "generated_at": self._utcnow_iso(),
        }

    def get_requests_export(
        self,
        *,
        state: Optional[str] = None,
        category_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        requests = self.list_requests(
            state=state,
            category_id=category_id,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
            assigned_to_id=assigned_to_id,
        )
        return {
            "total": len(requests),
            "pending_count": sum(
                1 for req in requests if req.state == ApprovalState.PENDING.value
            ),
            "terminal_count": sum(
                1
                for req in requests
                if req.state
                in {
                    ApprovalState.APPROVED.value,
                    ApprovalState.CANCELLED.value,
                }
            ),
            "requests": [
                (read_model := self.get_request_read_model(req.id)) | read_model["status"]
                for req in requests
            ],
            "filters": {
                "state": state,
                "category_id": category_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "priority": priority,
                "assigned_to_id": assigned_to_id,
            },
            "generated_at": self._utcnow_iso(),
        }

    def export_requests(
        self,
        *,
        fmt: str = "json",
        state: Optional[str] = None,
        category_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
    ) -> Dict[str, Any] | str:
        fmt = self._normalize_export_format(fmt)
        payload = self.get_requests_export(
            state=state,
            category_id=category_id,
            entity_type=entity_type,
            entity_id=entity_id,
            priority=priority,
            assigned_to_id=assigned_to_id,
        )
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(
                payload["requests"],
                [
                    "id",
                    "title",
                    "category_id",
                    "entity_type",
                    "entity_id",
                    "state",
                    "priority",
                    "assigned_to_id",
                    "requested_by_id",
                    "decided_by_id",
                    "created_at",
                    "submitted_at",
                    "decided_at",
                    "cancelled_at",
                    "age_hours",
                    "is_terminal",
                    "requires_decision",
                    "can_resubmit",
                    "is_assigned",
                    "latest_event_type",
                    "latest_event_at",
                    "milestone_count",
                ],
            )
        if fmt == "markdown":
            filters = payload["filters"]
            rows = payload["requests"]
            lines = [
                "# Approvals Requests Export",
                "",
                f"- generated_at: `{payload['generated_at']}`",
                f"- total: `{payload['total']}`",
                f"- pending_count: `{payload['pending_count']}`",
                f"- terminal_count: `{payload['terminal_count']}`",
                "",
                "## Filters",
                "",
            ]
            for key, value in filters.items():
                lines.append(f"- {key}: `{value}`")
            lines.extend(
                [
                    "",
                    "## Requests",
                    "",
                    self._render_markdown_table(
                        rows,
                        [
                            "id",
                            "title",
                            "state",
                            "priority",
                            "entity_type",
                            "entity_id",
                            "latest_event_type",
                            "latest_event_at",
                        ],
                    ),
                ]
            )
            return "\n".join(lines)
        raise ValueError(f"Unsupported format: {fmt}")

    def get_summary_export(
        self,
        *,
        entity_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        summary = self.get_summary(entity_type=entity_type, category_id=category_id)
        metrics: List[Dict[str, Any]] = [
            {"metric": "total", "value": summary["total"]},
            {"metric": "pending", "value": summary["pending"]},
            {"metric": "terminal_count", "value": summary["terminal_count"]},
            {"metric": "resubmittable_count", "value": summary["resubmittable_count"]},
            {"metric": "unassigned_pending_count", "value": summary["unassigned_pending_count"]},
        ]
        for key, value in sorted(summary["by_state"].items()):
            metrics.append({"metric": f"state.{key}", "value": value})
        for key, value in sorted(summary["by_priority"].items()):
            metrics.append({"metric": f"priority.{key}", "value": value})
        return {
            "summary": summary,
            "metrics": metrics,
            "generated_at": self._utcnow_iso(),
        }

    def export_summary(
        self,
        *,
        fmt: str = "json",
        entity_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any] | str:
        fmt = self._normalize_export_format(fmt)
        payload = self.get_summary_export(
            entity_type=entity_type,
            category_id=category_id,
        )
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(payload["metrics"], ["metric", "value"])
        if fmt == "markdown":
            lines = [
                "# Approvals Summary Export",
                "",
                f"- generated_at: `{payload['generated_at']}`",
                "",
                "## Summary",
                "",
                self._render_markdown_table(payload["metrics"], ["metric", "value"]),
            ]
            return "\n".join(lines)
        raise ValueError(f"Unsupported format: {fmt}")

    def get_ops_report(self) -> Dict[str, Any]:
        categories = self.list_categories()
        requests = self.list_requests()
        total_requests = len(requests)
        total_categories = len(categories)

        def _coverage(count: int) -> float:
            if total_requests == 0:
                return 0.0
            return round(count / total_requests, 4)

        category_count = sum(1 for req in requests if req.category_id)
        entity_link_count = sum(
            1 for req in requests if req.entity_type and req.entity_id
        )
        assignment_count = sum(1 for req in requests if req.assigned_to_id is not None)
        terminal_state_count = sum(
            1
            for req in requests
            if req.state
            in {
                ApprovalState.APPROVED.value,
                ApprovalState.REJECTED.value,
                ApprovalState.CANCELLED.value,
            }
        )

        category_coverage = _coverage(category_count)
        entity_link_coverage = _coverage(entity_link_count)
        assignment_coverage = _coverage(assignment_count)
        terminal_state_coverage = _coverage(terminal_state_count)
        pending_unassigned_total = sum(
            1
            for req in requests
            if req.state == ApprovalState.PENDING.value and req.assigned_to_id is None
        )
        latest_activity_at = max(
            (
                self._latest_request_activity_at(req)
                for req in requests
                if self._latest_request_activity_at(req) is not None
            ),
            default=None,
        )

        return {
            "generated_at": self._utcnow_iso(),
            "categories_total": total_categories,
            "requests_total": total_requests,
            "requires_decision_total": sum(
                1 for req in requests if req.state == ApprovalState.PENDING.value
            ),
            "pending_unassigned_total": pending_unassigned_total,
            "category_coverage": category_coverage,
            "entity_link_coverage": entity_link_coverage,
            "assignment_coverage": assignment_coverage,
            "terminal_state_coverage": terminal_state_coverage,
            "latest_activity_at": latest_activity_at,
            "bootstrap_ready": (
                total_categories > 0
                and total_requests > 0
                and category_coverage > 0
                and entity_link_coverage > 0
                and assignment_coverage > 0
            ),
        }

    def get_queue_health(
        self,
        *,
        stale_after_hours: int = 24,
        warn_after_hours: int = 4,
        entity_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if warn_after_hours <= 0:
            raise ValueError("warn_after_hours must be > 0")
        if stale_after_hours <= 0:
            raise ValueError("stale_after_hours must be > 0")
        if warn_after_hours >= stale_after_hours:
            raise ValueError("warn_after_hours must be less than stale_after_hours")

        requests = self.list_requests(
            entity_type=entity_type,
            category_id=category_id,
        )
        now = datetime.utcnow()
        pending_requests = [
            req for req in requests if req.state == ApprovalState.PENDING.value
        ]
        pending_rows: List[Dict[str, Any]] = []
        aged_pending_rows: List[Dict[str, Any]] = []
        pending_age_values: List[float] = []
        unassigned_pending_count = 0
        stale_pending_count = 0
        watch_pending_count = 0
        fresh_pending_count = 0

        for req in sorted(
            pending_requests,
            key=lambda item: self._normalize_datetime(item.created_at) or datetime.min,
        ):
            age_hours = self._age_hours(req.created_at, now)
            pending_rows.append(
                {
                    "id": req.id,
                    "title": req.title,
                    "category_id": req.category_id,
                    "entity_type": req.entity_type,
                    "entity_id": req.entity_id,
                    "priority": req.priority,
                    "assigned_to_id": req.assigned_to_id,
                    "requested_by_id": req.requested_by_id,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                    "age_hours": age_hours,
                }
            )
            if age_hours is None:
                continue
            aged_pending_rows.append(pending_rows[-1])
            pending_age_values.append(age_hours)
            if age_hours >= stale_after_hours:
                stale_pending_count += 1
            elif age_hours >= warn_after_hours:
                watch_pending_count += 1
            else:
                fresh_pending_count += 1
            if req.assigned_to_id is None:
                unassigned_pending_count += 1

        oldest_pending = aged_pending_rows[0] if aged_pending_rows else None
        oldest_pending_age_hours = pending_age_values[0] if pending_age_values else None
        average_pending_age_hours = (
            round(sum(pending_age_values) / len(pending_age_values), 2)
            if pending_age_values
            else None
        )
        pending_ratio = round(len(pending_rows) / len(requests), 4) if requests else 0.0

        risk_flags: List[str] = []
        if stale_pending_count > 0:
            risk_flags.append("stale_pending_backlog")
        if unassigned_pending_count > 0:
            risk_flags.append("unassigned_pending_work")
        if len(pending_rows) > 0 and pending_ratio >= 0.5:
            risk_flags.append("pending_pressure")

        by_state: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        for req in requests:
            by_state[req.state] = by_state.get(req.state, 0) + 1
            by_priority[req.priority] = by_priority.get(req.priority, 0) + 1

        return {
            "generated_at": self._utcnow_iso(),
            "filters": {
                "entity_type": entity_type,
                "category_id": category_id,
            },
            "thresholds": {
                "warn_after_hours": warn_after_hours,
                "stale_after_hours": stale_after_hours,
            },
            "total": len(requests),
            "pending": len(pending_rows),
            "pending_ratio": pending_ratio,
            "by_state": by_state,
            "by_priority": by_priority,
            "pending_age": {
                "oldest_hours": oldest_pending_age_hours,
                "average_hours": average_pending_age_hours,
                "oldest_request": oldest_pending,
                "fresh_count": fresh_pending_count,
                "watch_count": watch_pending_count,
                "stale_count": stale_pending_count,
            },
            "unassigned_pending_count": unassigned_pending_count,
            "risk_flags": risk_flags,
            "health_status": "degraded" if risk_flags else "healthy",
            "operational_ready": not risk_flags and len(requests) > 0,
        }

    def get_queue_health_export(
        self,
        *,
        stale_after_hours: int = 24,
        warn_after_hours: int = 4,
        entity_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        health = self.get_queue_health(
            stale_after_hours=stale_after_hours,
            warn_after_hours=warn_after_hours,
            entity_type=entity_type,
            category_id=category_id,
        )
        metrics: List[Dict[str, Any]] = [
            {"metric": "total", "value": health["total"]},
            {"metric": "pending", "value": health["pending"]},
            {"metric": "pending_ratio", "value": health["pending_ratio"]},
            {"metric": "stale_count", "value": health["pending_age"]["stale_count"]},
            {"metric": "watch_count", "value": health["pending_age"]["watch_count"]},
            {"metric": "fresh_count", "value": health["pending_age"]["fresh_count"]},
            {"metric": "oldest_pending_age_hours", "value": health["pending_age"]["oldest_hours"]},
            {"metric": "average_pending_age_hours", "value": health["pending_age"]["average_hours"]},
            {"metric": "unassigned_pending_count", "value": health["unassigned_pending_count"]},
            {"metric": "health_status", "value": health["health_status"]},
            {"metric": "risk_flags", "value": ";".join(health["risk_flags"])},
        ]
        return {
            "health": health,
            "metrics": metrics,
            "generated_at": health["generated_at"],
        }

    def export_queue_health(
        self,
        *,
        fmt: str = "json",
        stale_after_hours: int = 24,
        warn_after_hours: int = 4,
        entity_type: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Dict[str, Any] | str:
        fmt = self._normalize_export_format(fmt)
        payload = self.get_queue_health_export(
            stale_after_hours=stale_after_hours,
            warn_after_hours=warn_after_hours,
            entity_type=entity_type,
            category_id=category_id,
        )
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(payload["metrics"], ["metric", "value"])
        if fmt == "markdown":
            health = payload["health"]
            lines = [
                "# Approvals Queue Health",
                "",
                f"- generated_at: `{payload['generated_at']}`",
                f"- health_status: `{health['health_status']}`",
                f"- operational_ready: `{health['operational_ready']}`",
                f"- total: `{health['total']}`",
                f"- pending: `{health['pending']}`",
                f"- risk_flags: `{';'.join(health['risk_flags'])}`",
                "",
                "## Metrics",
                "",
                self._render_markdown_table(payload["metrics"], ["metric", "value"]),
            ]
            return "\n".join(lines)
        raise ValueError(f"Unsupported format: {fmt}")

    def export_ops_report(self, *, fmt: str = "json") -> Dict[str, Any] | str:
        fmt = self._normalize_export_format(fmt)
        payload = self.get_ops_report()
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv([payload], list(payload.keys()))
        if fmt == "markdown":
            lines = [
                "# Approvals Ops Report",
                "",
                self._render_markdown_table(
                    [{k: payload[k] for k in payload.keys()}],
                    list(payload.keys()),
                ),
            ]
            return "\n".join(lines)
        raise ValueError(f"Unsupported format: {fmt}")
