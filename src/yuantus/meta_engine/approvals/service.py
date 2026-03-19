"""Generic approvals service layer."""
from __future__ import annotations

import csv
import uuid
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.approvals.models import (
    ApprovalCategory,
    ApprovalPriority,
    ApprovalRequest,
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
    def _request_dict(req: ApprovalRequest) -> Dict[str, Any]:
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
        }

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
    ) -> ApprovalRequest:
        if priority not in {e.value for e in ApprovalPriority}:
            raise ValueError(f"Invalid priority: {priority}")

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
        )
        self.session.add(req)
        self.session.flush()
        return req

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self.session.get(ApprovalRequest, request_id)

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
        req.state = target_state

        if target_state == ApprovalState.PENDING.value:
            req.submitted_at = now
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

        self.session.flush()
        return req

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
        return {
            "total": len(requests),
            "pending": pending,
            "by_state": by_state,
            "by_priority": by_priority,
            "filters": {
                "entity_type": entity_type,
                "category_id": category_id,
            },
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
            "requests": [self._request_dict(req) for req in requests],
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
                ],
            )
        if fmt == "markdown":
            filters = payload["filters"]
            rows = payload["requests"]
            lines = [
                "# Approvals Requests Export",
                "",
                f"- generated_at: `{payload['generated_at']}`",
                f"- total: `{len(rows)}`",
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
                        ["id", "title", "state", "priority", "entity_type", "entity_id"],
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

        return {
            "generated_at": self._utcnow_iso(),
            "categories_total": total_categories,
            "requests_total": total_requests,
            "category_coverage": category_coverage,
            "entity_link_coverage": entity_link_coverage,
            "assignment_coverage": assignment_coverage,
            "terminal_state_coverage": terminal_state_coverage,
            "bootstrap_ready": (
                total_categories > 0
                and total_requests > 0
                and category_coverage > 0
                and entity_link_coverage > 0
                and assignment_coverage > 0
            ),
        }

    def export_ops_report(self, *, fmt: str = "json") -> Dict[str, Any] | str:
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
