"""Generic approvals service layer."""
from __future__ import annotations

import uuid
from datetime import datetime
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
