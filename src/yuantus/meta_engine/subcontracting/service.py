"""Subcontracting bootstrap service."""
from __future__ import annotations

import csv
import uuid
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.manufacturing.models import Operation
from yuantus.meta_engine.subcontracting.models import (
    SubcontractApprovalRoleMapping,
    SubcontractEventType,
    SubcontractOrder,
    SubcontractOrderEvent,
    SubcontractOrderState,
)


class SubcontractingService:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.utcnow().isoformat() + "Z"

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
        if not rows:
            return "_No rows_"
        header = "| " + " | ".join(columns) + " |"
        divider = "| " + " | ".join("---" for _ in columns) + " |"
        body = [
            "| " + " | ".join(str(row.get(column, "") or "") for column in columns) + " |"
            for row in rows
        ]
        return "\n".join([header, divider, *body])

    @staticmethod
    def _normalize_export_format(fmt: str) -> str:
        normalized = str(fmt or "json").strip().lower()
        if normalized not in {"json", "csv", "markdown"}:
            raise ValueError("fmt must be one of: json, csv, markdown")
        return normalized

    @staticmethod
    def _summarize_counts(rows: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for row in rows:
            bucket = str(row.get(key) or "none")
            counts[bucket] = counts.get(bucket, 0) + 1
        return counts

    def create_order(
        self,
        *,
        name: str,
        requested_qty: float,
        item_id: Optional[str] = None,
        routing_id: Optional[str] = None,
        source_operation_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        vendor_name: Optional[str] = None,
        note: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> SubcontractOrder:
        if requested_qty <= 0:
            raise ValueError("requested_qty must be > 0")
        operation = self._get_operation(source_operation_id) if source_operation_id else None
        order = SubcontractOrder(
            id=str(uuid.uuid4()),
            name=name,
            item_id=item_id,
            routing_id=routing_id or getattr(operation, "routing_id", None),
            source_operation_id=source_operation_id,
            vendor_id=vendor_id or getattr(operation, "subcontractor_id", None),
            vendor_name=vendor_name,
            state=SubcontractOrderState.DRAFT.value,
            requested_qty=requested_qty,
            note=note,
            properties=properties or {},
            created_by_id=user_id,
        )
        self.session.add(order)
        self.session.flush()
        return order

    def list_orders(
        self,
        *,
        state: Optional[str] = None,
        vendor_id: Optional[str] = None,
        routing_id: Optional[str] = None,
        source_operation_id: Optional[str] = None,
    ) -> List[SubcontractOrder]:
        orders = self.session.query(SubcontractOrder).order_by(
            SubcontractOrder.created_at.desc()
        ).all()
        if state is not None:
            orders = [order for order in orders if order.state == state]
        if vendor_id is not None:
            orders = [order for order in orders if order.vendor_id == vendor_id]
        if routing_id is not None:
            orders = [order for order in orders if order.routing_id == routing_id]
        if source_operation_id is not None:
            orders = [
                order
                for order in orders
                if order.source_operation_id == source_operation_id
            ]
        return orders

    def get_order(self, order_id: str) -> Optional[SubcontractOrder]:
        return self.session.get(SubcontractOrder, order_id)

    @staticmethod
    def _compose_approval_role_mapping_scope_value(
        *,
        scope_type: str,
        scope_value: Optional[str] = None,
        scope_vendor_id: Optional[str] = None,
        scope_policy_code: Optional[str] = None,
    ) -> Optional[str]:
        normalized_scope_type = str(scope_type or "").strip().lower()
        normalized_scope_value = str(scope_value or "").strip() or None
        vendor_value = str(scope_vendor_id or "").strip() or None
        policy_value = str(scope_policy_code or "").strip().lower() or None
        if normalized_scope_type == "vendor":
            return normalized_scope_value or vendor_value
        if normalized_scope_type == "policy_code":
            return normalized_scope_value or policy_value
        if normalized_scope_type != "vendor_policy":
            return normalized_scope_value
        if normalized_scope_value and "::" in normalized_scope_value:
            vendor_part, policy_part = normalized_scope_value.split("::", 1)
            vendor_value = vendor_value or str(vendor_part or "").strip() or None
            policy_value = policy_value or str(policy_part or "").strip().lower() or None
        if not vendor_value or not policy_value:
            raise ValueError("vendor_policy scope requires scope_vendor_id and scope_policy_code")
        return f"{vendor_value}::{policy_value}"

    @staticmethod
    def _expand_approval_role_mapping_scope(
        *,
        scope_type: Optional[str],
        scope_value: Optional[str],
    ) -> Dict[str, Optional[str]]:
        normalized_scope_type = str(scope_type or "").strip().lower() or None
        normalized_scope_value = str(scope_value or "").strip() or None
        payload = {
            "scope_type": normalized_scope_type,
            "scope_value": normalized_scope_value,
            "scope_vendor_id": None,
            "scope_policy_code": None,
        }
        if normalized_scope_type == "vendor_policy" and normalized_scope_value and "::" in normalized_scope_value:
            vendor_id, policy_code = normalized_scope_value.split("::", 1)
            payload["scope_vendor_id"] = str(vendor_id or "").strip() or None
            payload["scope_policy_code"] = str(policy_code or "").strip().lower() or None
        elif normalized_scope_type == "vendor":
            payload["scope_vendor_id"] = normalized_scope_value
        elif normalized_scope_type == "policy_code":
            payload["scope_policy_code"] = (
                str(normalized_scope_value or "").strip().lower() or None
            )
        return payload

    @staticmethod
    def _approval_role_mapping_scope_rank(scope_type: Optional[str]) -> int:
        normalized_scope_type = str(scope_type or "").strip().lower()
        return {
            "vendor_policy": 0,
            "vendor": 1,
            "policy_code": 2,
            "team": 3,
            "global": 4,
        }.get(normalized_scope_type, 9)

    @staticmethod
    def _approval_role_mapping_scope_label(scope_type: Optional[str], scope_value: Optional[str]) -> str:
        expanded = SubcontractingService._expand_approval_role_mapping_scope(
            scope_type=scope_type,
            scope_value=scope_value,
        )
        normalized_scope_type = expanded["scope_type"] or "global"
        if normalized_scope_type == "vendor_policy":
            return f"vendor:{expanded['scope_vendor_id']} / policy:{expanded['scope_policy_code']}"
        if normalized_scope_type == "vendor":
            return f"vendor:{expanded['scope_vendor_id']}"
        if normalized_scope_type == "policy_code":
            return f"policy:{expanded['scope_policy_code']}"
        if normalized_scope_type == "team":
            return f"team:{expanded['scope_value']}"
        return "global"

    def list_approval_role_mappings(
        self,
        *,
        scope_type: Optional[str] = None,
        scope_value: Optional[str] = None,
        scope_vendor_id: Optional[str] = None,
        scope_policy_code: Optional[str] = None,
        role_code: Optional[str] = None,
        active_only: bool = True,
    ) -> List[SubcontractApprovalRoleMapping]:
        mappings = self.session.query(SubcontractApprovalRoleMapping).order_by(
            SubcontractApprovalRoleMapping.sequence.asc(),
            SubcontractApprovalRoleMapping.created_at.asc(),
        ).all()
        normalized_scope_type = str(scope_type or "").strip().lower() or None
        if normalized_scope_type is None:
            if str(scope_vendor_id or "").strip() and str(scope_policy_code or "").strip():
                normalized_scope_type = "vendor_policy"
            elif str(scope_vendor_id or "").strip():
                normalized_scope_type = "vendor"
            elif str(scope_policy_code or "").strip():
                normalized_scope_type = "policy_code"
        if normalized_scope_type is not None:
            mappings = [
                item
                for item in mappings
                if str(item.scope_type or "").strip().lower() == normalized_scope_type
            ]
        if normalized_scope_type is not None:
            normalized_scope_value = self._compose_approval_role_mapping_scope_value(
                scope_type=normalized_scope_type,
                scope_value=scope_value,
                scope_vendor_id=scope_vendor_id,
                scope_policy_code=scope_policy_code,
            )
        else:
            normalized_scope_value = str(scope_value or "").strip() or None
        if normalized_scope_value is not None:
            mappings = [
                item
                for item in mappings
                if (str(item.scope_value or "").strip() or None) == normalized_scope_value
            ]
        normalized_role_code = str(role_code or "").strip().lower() or None
        if normalized_role_code is not None:
            mappings = [
                item
                for item in mappings
                if str(item.role_code or "").strip().lower() == normalized_role_code
            ]
        if active_only:
            mappings = [item for item in mappings if bool(item.active)]
        return mappings

    def upsert_approval_role_mapping(
        self,
        *,
        role_code: str,
        scope_type: str,
        scope_value: Optional[str] = None,
        scope_vendor_id: Optional[str] = None,
        scope_policy_code: Optional[str] = None,
        owner: Optional[str] = None,
        team: Optional[str] = None,
        required: bool = False,
        sequence: int = 10,
        fallback_role: Optional[str] = None,
        active: bool = True,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> SubcontractApprovalRoleMapping:
        normalized_role_code = str(role_code or "").strip().lower()
        if not normalized_role_code:
            raise ValueError("role_code required")
        normalized_scope_type = str(scope_type or "").strip().lower()
        if normalized_scope_type not in {"global", "vendor", "team", "policy_code", "vendor_policy"}:
            raise ValueError(
                "scope_type must be one of: global, vendor, team, policy_code, vendor_policy"
            )
        normalized_scope_value = self._compose_approval_role_mapping_scope_value(
            scope_type=normalized_scope_type,
            scope_value=scope_value,
            scope_vendor_id=scope_vendor_id,
            scope_policy_code=scope_policy_code,
        )
        if normalized_scope_type != "global" and not normalized_scope_value:
            raise ValueError("scope_value required for non-global scope")
        normalized_owner = str(owner or "").strip() or None
        normalized_team = str(team or "").strip() or None
        if not normalized_owner and not normalized_team:
            raise ValueError("owner or team required")
        if sequence <= 0:
            raise ValueError("sequence must be > 0")
        normalized_fallback_role = str(fallback_role or "").strip().lower() or None
        existing = next(
            (
                item
                for item in self.list_approval_role_mappings(active_only=False)
                if str(item.role_code or "").strip().lower() == normalized_role_code
                and str(item.scope_type or "").strip().lower() == normalized_scope_type
                and (str(item.scope_value or "").strip() or None) == normalized_scope_value
                and int(item.sequence or 0) == int(sequence)
            ),
            None,
        )
        mapping = existing or SubcontractApprovalRoleMapping(
            id=str(uuid.uuid4()),
            role_code=normalized_role_code,
            scope_type=normalized_scope_type,
            scope_value=normalized_scope_value,
        )
        mapping.owner = normalized_owner
        mapping.team = normalized_team
        mapping.required = bool(required)
        mapping.sequence = int(sequence)
        mapping.fallback_role = normalized_fallback_role
        mapping.active = bool(active)
        merged_properties = dict(mapping.properties or {})
        merged_properties.update(dict(properties or {}))
        mapping.properties = merged_properties
        mapping.created_by_id = user_id
        if existing is None:
            self.session.add(mapping)
        self.session.flush()
        return mapping

    def _resolve_approval_role_mapping(
        self,
        *,
        role_code: Optional[str],
        vendor_id: Optional[str] = None,
        team: Optional[str] = None,
        policy_code: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        normalized_role_code = str(role_code or "").strip().lower() or None
        if not normalized_role_code:
            return {}
        candidates: List[SubcontractApprovalRoleMapping] = []
        if str(vendor_id or "").strip() and str(policy_code or "").strip():
            candidates.extend(
                self.list_approval_role_mappings(
                    scope_type="vendor_policy",
                    scope_vendor_id=vendor_id,
                    scope_policy_code=policy_code,
                    role_code=normalized_role_code,
                )
            )
        if str(vendor_id or "").strip():
            candidates.extend(
                self.list_approval_role_mappings(
                    scope_type="vendor",
                    scope_vendor_id=vendor_id,
                    role_code=normalized_role_code,
                )
            )
        if str(policy_code or "").strip():
            candidates.extend(
                self.list_approval_role_mappings(
                    scope_type="policy_code",
                    scope_policy_code=policy_code,
                    role_code=normalized_role_code,
                )
            )
        if str(team or "").strip():
            candidates.extend(
                self.list_approval_role_mappings(
                    scope_type="team",
                    scope_value=team,
                    role_code=normalized_role_code,
                )
            )
        candidates.extend(
            self.list_approval_role_mappings(
                scope_type="global",
                role_code=normalized_role_code,
            )
        )
        if not candidates:
            return {}
        candidates.sort(
            key=lambda item: (
                self._approval_role_mapping_scope_rank(item.scope_type),
                int(item.sequence or 0),
                str(item.id or ""),
            )
        )
        selected = candidates[0]
        return {
            "mapping_id": selected.id,
            "owner": str(selected.owner or "").strip() or None,
            "team": str(selected.team or "").strip() or None,
            "scope_type": str(selected.scope_type or "").strip().lower() or None,
            "scope_value": str(selected.scope_value or "").strip() or None,
        }

    def get_approval_role_mapping_registry(
        self,
        *,
        scope_type: Optional[str] = None,
        scope_value: Optional[str] = None,
        scope_vendor_id: Optional[str] = None,
        scope_policy_code: Optional[str] = None,
        role_code: Optional[str] = None,
        active_only: bool = True,
        limit: int = 200,
        sort_by: str = "scope",
    ) -> Dict[str, Any]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        normalized_sort = (sort_by or "scope").strip().lower()
        if normalized_sort not in {"scope", "role", "sequence"}:
            raise ValueError("sort_by must be one of: scope, role, sequence")
        normalized_scope_type = str(scope_type or "").strip().lower() or None
        if normalized_scope_type is None:
            if str(scope_vendor_id or "").strip() and str(scope_policy_code or "").strip():
                normalized_scope_type = "vendor_policy"
            elif str(scope_vendor_id or "").strip():
                normalized_scope_type = "vendor"
            elif str(scope_policy_code or "").strip():
                normalized_scope_type = "policy_code"
        if normalized_scope_type is not None:
            normalized_scope_value = self._compose_approval_role_mapping_scope_value(
                scope_type=normalized_scope_type,
                scope_value=scope_value,
                scope_vendor_id=scope_vendor_id,
                scope_policy_code=scope_policy_code,
            )
        else:
            normalized_scope_value = str(scope_value or "").strip() or None
        rows: List[Dict[str, Any]] = []
        for mapping in self.list_approval_role_mappings(
            scope_type=normalized_scope_type,
            scope_value=normalized_scope_value,
            scope_vendor_id=scope_vendor_id,
            scope_policy_code=scope_policy_code,
            role_code=role_code,
            active_only=active_only,
        ):
            expanded = self._expand_approval_role_mapping_scope(
                scope_type=mapping.scope_type,
                scope_value=mapping.scope_value,
            )
            fallback = (
                self._resolve_approval_role_mapping(
                    role_code=mapping.fallback_role,
                    vendor_id=expanded["scope_vendor_id"],
                    team=expanded["scope_value"] if expanded["scope_type"] == "team" else None,
                    policy_code=expanded["scope_policy_code"],
                )
                if str(mapping.fallback_role or "").strip()
                else {}
            )
            rows.append(
                {
                    "id": mapping.id,
                    "role_code": str(mapping.role_code or "").strip().lower() or None,
                    "scope_type": expanded["scope_type"],
                    "scope_value": expanded["scope_value"],
                    "scope_vendor_id": expanded["scope_vendor_id"],
                    "scope_policy_code": expanded["scope_policy_code"],
                    "scope_label": self._approval_role_mapping_scope_label(
                        mapping.scope_type,
                        mapping.scope_value,
                    ),
                    "owner": str(mapping.owner or "").strip() or None,
                    "team": str(mapping.team or "").strip() or None,
                    "required": bool(mapping.required),
                    "sequence": int(mapping.sequence or 0),
                    "fallback_role": str(mapping.fallback_role or "").strip().lower() or None,
                    "fallback_owner": fallback.get("owner"),
                    "fallback_team": fallback.get("team"),
                    "active": bool(mapping.active),
                    "properties": dict(mapping.properties or {}),
                    "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
                    "created_by_id": mapping.created_by_id,
                    "resolution_precedence": "manual > role_mapping > fallback",
                }
            )
        if normalized_sort == "role":
            rows.sort(
                key=lambda row: (
                    row.get("role_code") or "",
                    self._approval_role_mapping_scope_rank(row.get("scope_type")),
                    int(row.get("sequence") or 0),
                    row.get("id") or "",
                )
            )
        elif normalized_sort == "sequence":
            rows.sort(
                key=lambda row: (
                    int(row.get("sequence") or 0),
                    self._approval_role_mapping_scope_rank(row.get("scope_type")),
                    row.get("role_code") or "",
                    row.get("id") or "",
                )
            )
        else:
            rows.sort(
                key=lambda row: (
                    self._approval_role_mapping_scope_rank(row.get("scope_type")),
                    row.get("scope_value") or "",
                    row.get("role_code") or "",
                    int(row.get("sequence") or 0),
                    row.get("id") or "",
                )
            )
        rows = rows[:limit]
        return {
            "generated_at": self._utcnow_iso(),
            "filters": {
                "scope_type": normalized_scope_type,
                "scope_value": normalized_scope_value,
                "scope_vendor_id": str(scope_vendor_id or "").strip() or None,
                "scope_policy_code": str(scope_policy_code or "").strip().lower() or None,
                "role_code": str(role_code or "").strip().lower() or None,
                "active_only": active_only,
                "limit": limit,
                "sort_by": normalized_sort,
            },
            "total": len(rows),
            "active_total": sum(1 for row in rows if row.get("active")),
            "required_total": sum(1 for row in rows if row.get("required")),
            "fallback_total": sum(1 for row in rows if row.get("fallback_role")),
            "scope_breakdown": self._summarize_counts(rows, "scope_type"),
            "role_breakdown": self._summarize_counts(rows, "role_code"),
            "resolution_precedence": [
                "vendor_policy",
                "vendor",
                "policy_code",
                "team",
                "global",
            ],
            "rows": rows,
        }

    def export_approval_role_mapping_registry(
        self,
        *,
        fmt: str = "json",
        scope_type: Optional[str] = None,
        scope_value: Optional[str] = None,
        scope_vendor_id: Optional[str] = None,
        scope_policy_code: Optional[str] = None,
        role_code: Optional[str] = None,
        active_only: bool = True,
        limit: int = 200,
        sort_by: str = "scope",
    ) -> Dict[str, Any] | str:
        fmt = self._normalize_export_format(fmt)
        payload = self.get_approval_role_mapping_registry(
            scope_type=scope_type,
            scope_value=scope_value,
            scope_vendor_id=scope_vendor_id,
            scope_policy_code=scope_policy_code,
            role_code=role_code,
            active_only=active_only,
            limit=limit,
            sort_by=sort_by,
        )
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(
                payload["rows"],
                [
                    "id",
                    "role_code",
                    "scope_type",
                    "scope_value",
                    "scope_vendor_id",
                    "scope_policy_code",
                    "scope_label",
                    "owner",
                    "team",
                    "required",
                    "sequence",
                    "fallback_role",
                    "fallback_owner",
                    "fallback_team",
                    "active",
                    "created_at",
                ],
            )
        return "\n".join(
            [
                "# Approval Role Mapping Registry",
                "",
                f"- total: `{payload['total']}`",
                f"- active_total: `{payload['active_total']}`",
                f"- required_total: `{payload['required_total']}`",
                f"- fallback_total: `{payload['fallback_total']}`",
                f"- resolution_precedence: `{', '.join(payload['resolution_precedence'])}`",
                "",
                self._render_markdown_table(
                    payload["rows"],
                    [
                        "role_code",
                        "scope_type",
                        "scope_value",
                        "scope_vendor_id",
                        "scope_policy_code",
                        "owner",
                        "team",
                        "required",
                        "sequence",
                        "fallback_role",
                    ],
                ),
            ]
        )

    def assign_vendor(
        self,
        order_id: str,
        *,
        vendor_id: str,
        vendor_name: Optional[str] = None,
    ) -> SubcontractOrder:
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        order.vendor_id = vendor_id
        if vendor_name is not None:
            order.vendor_name = vendor_name
        self.session.flush()
        return order

    def record_material_issue(
        self,
        order_id: str,
        *,
        quantity: float,
        reference: Optional[str] = None,
        note: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> SubcontractOrderEvent:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        order.issued_qty = float(order.issued_qty or 0.0) + quantity
        if order.issued_qty > 0:
            order.state = SubcontractOrderState.ISSUED.value
        event = self._create_event(
            order_id=order_id,
            event_type=SubcontractEventType.MATERIAL_ISSUE.value,
            quantity=quantity,
            reference=reference,
            note=note,
            user_id=user_id,
        )
        self.session.flush()
        return event

    def record_receipt(
        self,
        order_id: str,
        *,
        quantity: float,
        reference: Optional[str] = None,
        note: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> SubcontractOrderEvent:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        order.received_qty = float(order.received_qty or 0.0) + quantity
        if order.received_qty >= float(order.requested_qty or 0.0):
            order.state = SubcontractOrderState.COMPLETED.value
        else:
            order.state = SubcontractOrderState.PARTIALLY_RECEIVED.value
        event = self._create_event(
            order_id=order_id,
            event_type=SubcontractEventType.RECEIPT.value,
            quantity=quantity,
            reference=reference,
            note=note,
            user_id=user_id,
        )
        self.session.flush()
        return event

    def get_timeline(self, order_id: str) -> List[SubcontractOrderEvent]:
        events = self.session.query(SubcontractOrderEvent).order_by(
            SubcontractOrderEvent.created_at.asc()
        )
        return [event for event in events.all() if event.order_id == order_id]

    def get_order_read_model(self, order_id: str) -> Dict[str, Any]:
        order = self.get_order(order_id)
        if not order:
            raise ValueError(f"SubcontractOrder {order_id} not found")
        operation = self._get_operation(order.source_operation_id) if order.source_operation_id else None
        timeline = self.get_timeline(order.id)
        requested_qty = float(order.requested_qty or 0.0)
        received_qty = float(order.received_qty or 0.0)
        completion_pct = round((received_qty / requested_qty) * 100, 2) if requested_qty > 0 else 0.0
        return {
            "id": order.id,
            "name": order.name,
            "item_id": order.item_id,
            "routing_id": order.routing_id,
            "source_operation_id": order.source_operation_id,
            "state": order.state,
            "vendor_id": order.vendor_id,
            "vendor_name": order.vendor_name,
            "requested_qty": requested_qty,
            "issued_qty": float(order.issued_qty or 0.0),
            "received_qty": received_qty,
            "open_qty": max(requested_qty - received_qty, 0.0),
            "completion_pct": completion_pct,
            "timeline_total": len(timeline),
            "operation": {
                "operation_id": getattr(operation, "id", None),
                "routing_id": getattr(operation, "routing_id", None),
                "operation_number": getattr(operation, "operation_number", None),
                "name": getattr(operation, "name", None),
                "is_subcontracted": bool(getattr(operation, "is_subcontracted", False)) if operation else False,
                "subcontractor_id": getattr(operation, "subcontractor_id", None),
            },
        }

    def _create_event(
        self,
        *,
        order_id: str,
        event_type: str,
        quantity: float,
        reference: Optional[str],
        note: Optional[str],
        user_id: Optional[int],
    ) -> SubcontractOrderEvent:
        event = SubcontractOrderEvent(
            id=str(uuid.uuid4()),
            order_id=order_id,
            event_type=event_type,
            quantity=quantity,
            reference=reference,
            note=note,
            created_by_id=user_id,
            properties={},
        )
        self.session.add(event)
        return event

    def _get_operation(self, operation_id: Optional[str]) -> Optional[Operation]:
        if not operation_id:
            return None
        return self.session.get(Operation, operation_id)

    def get_overview(self) -> Dict[str, Any]:
        orders = self.list_orders()
        total_requested = sum(float(order.requested_qty or 0.0) for order in orders)
        total_issued = sum(float(order.issued_qty or 0.0) for order in orders)
        total_received = sum(float(order.received_qty or 0.0) for order in orders)
        by_state: Dict[str, int] = {}
        for order in orders:
            by_state[order.state] = by_state.get(order.state, 0) + 1
        return {
            "generated_at": self._utcnow_iso(),
            "orders_total": len(orders),
            "vendors_total": len({order.vendor_id for order in orders if order.vendor_id}),
            "requested_qty_total": round(total_requested, 4),
            "issued_qty_total": round(total_issued, 4),
            "received_qty_total": round(total_received, 4),
            "open_qty_total": round(max(total_requested - total_received, 0.0), 4),
            "by_state": by_state,
        }

    def get_vendor_analytics(self) -> Dict[str, Any]:
        rows: Dict[str, Dict[str, Any]] = {}
        for order in self.list_orders():
            vendor_key = order.vendor_id or "unassigned"
            current = rows.setdefault(
                vendor_key,
                {
                    "vendor_id": order.vendor_id,
                    "vendor_name": order.vendor_name,
                    "orders_total": 0,
                    "requested_qty_total": 0.0,
                    "issued_qty_total": 0.0,
                    "received_qty_total": 0.0,
                    "open_qty_total": 0.0,
                },
            )
            requested = float(order.requested_qty or 0.0)
            issued = float(order.issued_qty or 0.0)
            received = float(order.received_qty or 0.0)
            current["orders_total"] += 1
            current["requested_qty_total"] += requested
            current["issued_qty_total"] += issued
            current["received_qty_total"] += received
            current["open_qty_total"] += max(requested - received, 0.0)
        vendors = list(rows.values())
        vendors.sort(key=lambda row: ((row["vendor_id"] or ""), row["vendor_name"] or ""))
        for vendor in vendors:
            requested = vendor["requested_qty_total"]
            received = vendor["received_qty_total"]
            vendor["completion_pct"] = round((received / requested) * 100, 2) if requested > 0 else 0.0
        return {
            "generated_at": self._utcnow_iso(),
            "vendors": vendors,
        }

    def get_receipt_analytics(self) -> Dict[str, Any]:
        rows = []
        for order in self.list_orders():
            requested = float(order.requested_qty or 0.0)
            received = float(order.received_qty or 0.0)
            rows.append(
                {
                    "order_id": order.id,
                    "name": order.name,
                    "vendor_id": order.vendor_id,
                    "state": order.state,
                    "requested_qty": requested,
                    "received_qty": received,
                    "open_qty": max(requested - received, 0.0),
                    "completion_pct": round((received / requested) * 100, 2) if requested > 0 else 0.0,
                }
            )
        rows.sort(key=lambda row: row["order_id"])
        return {
            "generated_at": self._utcnow_iso(),
            "receipts": rows,
        }

    def export_overview(self, *, fmt: str = "json") -> Dict[str, Any] | str:
        payload = self.get_overview()
        if fmt == "json":
            return payload
        if fmt == "csv":
            flattened = {
                "generated_at": payload["generated_at"],
                "orders_total": payload["orders_total"],
                "vendors_total": payload["vendors_total"],
                "requested_qty_total": payload["requested_qty_total"],
                "issued_qty_total": payload["issued_qty_total"],
                "received_qty_total": payload["received_qty_total"],
                "open_qty_total": payload["open_qty_total"],
                "by_state": payload["by_state"],
            }
            return self._render_csv([flattened], list(flattened.keys()))
        raise ValueError(f"Unsupported format: {fmt}")

    def export_vendor_analytics(self, *, fmt: str = "json") -> Dict[str, Any] | str:
        payload = self.get_vendor_analytics()
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(
                payload["vendors"],
                [
                    "vendor_id",
                    "vendor_name",
                    "orders_total",
                    "requested_qty_total",
                    "issued_qty_total",
                    "received_qty_total",
                    "open_qty_total",
                    "completion_pct",
                ],
            )
        raise ValueError(f"Unsupported format: {fmt}")

    def export_receipt_analytics(self, *, fmt: str = "json") -> Dict[str, Any] | str:
        payload = self.get_receipt_analytics()
        if fmt == "json":
            return payload
        if fmt == "csv":
            return self._render_csv(
                payload["receipts"],
                [
                    "order_id",
                    "name",
                    "vendor_id",
                    "state",
                    "requested_qty",
                    "received_qty",
                    "open_qty",
                    "completion_pct",
                ],
            )
        raise ValueError(f"Unsupported format: {fmt}")
