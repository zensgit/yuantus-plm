from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from yuantus.integrations.cad_connectors import resolve_cad_sync_key
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.cad_service import normalize_cad_attributes


def _json_text(expr):
    if hasattr(expr, "as_string"):
        return expr.as_string()
    if hasattr(expr, "astext"):
        return expr.astext
    return cast(expr, String)


def _normalize_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_node_value(node: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        if key in node and node[key] is not None:
            return node[key]
        lower = key.lower()
        for k, v in node.items():
            if str(k).lower() == lower and v is not None:
                return v
    return None


def _parse_quantity(value: Any, default: float = 1.0) -> float:
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return default


def _normalize_refdes(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(v).strip() for v in value if str(v).strip()]
        return ",".join(sorted(set(items))) if items else None
    text = str(value).strip()
    return text or None


def _normalize_bom_payload(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    root = payload.get("root")
    if isinstance(nodes, list) and isinstance(edges, list):
        return nodes, edges, root if isinstance(root, str) else None

    root_node = None
    if isinstance(root, dict):
        root_node = root
    elif isinstance(payload, dict) and "children" in payload:
        root_node = payload

    if not root_node:
        return [], [], None

    flat_nodes: List[Dict[str, Any]] = []
    flat_edges: List[Dict[str, Any]] = []

    def _resolve_node_id(node: Dict[str, Any], index: int) -> str:
        candidate = _extract_node_value(
            node, "id", "uid", "node_id", "part_number", "item_number", "number"
        )
        return str(candidate) if candidate else f"node-{index}"

    def _walk(node: Dict[str, Any], parent_id: Optional[str], counter: List[int]) -> str:
        counter[0] += 1
        node_id = _resolve_node_id(node, counter[0])
        node = dict(node)
        node["id"] = node_id
        flat_nodes.append(node)
        if parent_id:
            edge: Dict[str, Any] = {"parent": parent_id, "child": node_id}
            for key in ("quantity", "qty", "uom", "find_num", "refdes"):
                if key in node:
                    edge[key] = node.get(key)
            flat_edges.append(edge)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                _walk(child, node_id, counter)
        return node_id

    root_id = _walk(root_node, None, [0])
    return flat_nodes, flat_edges, root_id


CAD_BOM_CONTRACT_SCHEMA = "nodes_edges_v1"


def _detect_bom_payload_shape(payload: Dict[str, Any]) -> str:
    if not payload:
        return "empty"
    if isinstance(payload.get("nodes"), list) and isinstance(payload.get("edges"), list):
        return "graph"
    if isinstance(payload.get("root"), dict) or (
        "children" in payload and isinstance(payload.get("children"), list)
    ):
        return "tree"
    return "unknown"


def prepare_cad_bom_payload(
    bom_payload: Optional[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str], Dict[str, Any]]:
    payload = bom_payload if isinstance(bom_payload, dict) else {}
    shape = _detect_bom_payload_shape(payload)
    raw_nodes, raw_edges, raw_root = _normalize_bom_payload(payload)
    issues: List[str] = []
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids: Set[str] = set()

    if shape == "unknown":
        issues.append("payload must expose nodes/edges arrays or a nested root/children tree")

    for index, raw_node in enumerate(raw_nodes):
        if not isinstance(raw_node, dict):
            issues.append(f"node[{index}] must be an object")
            continue
        node_id = _normalize_text(
            _extract_node_value(
                raw_node, "id", "uid", "node_id", "part_number", "item_number", "number"
            )
        )
        if not node_id:
            issues.append(f"node[{index}] missing id")
            continue
        if node_id in node_ids:
            issues.append(f"duplicate node id: {node_id}")
            continue
        node_copy = dict(raw_node)
        node_copy["id"] = node_id
        nodes.append(node_copy)
        node_ids.add(node_id)

    accepted_edge_count = 0
    indegree = {node_id: 0 for node_id in node_ids}

    for index, raw_edge in enumerate(raw_edges):
        if not isinstance(raw_edge, dict):
            issues.append(f"edge[{index}] must be an object")
            continue
        edges.append(raw_edge)
        parent = _normalize_text(_extract_node_value(raw_edge, "parent", "from", "source"))
        child = _normalize_text(_extract_node_value(raw_edge, "child", "to", "target"))
        if not parent:
            issues.append(f"edge[{index}] missing parent")
            continue
        if not child:
            issues.append(f"edge[{index}] missing child")
            continue
        if parent not in node_ids:
            issues.append(f"edge[{index}] parent not found: {parent}")
            continue
        if child not in node_ids:
            issues.append(f"edge[{index}] child not found: {child}")
            continue
        indegree[child] = indegree.get(child, 0) + 1
        accepted_edge_count += 1

    root = raw_root if raw_root in node_ids else None
    root_source: Optional[str] = None
    if root:
        root_source = "payload"
    elif raw_root:
        issues.append(f"root not found: {raw_root}")

    if not root and node_ids:
        root_candidates = sorted(node_id for node_id, degree in indegree.items() if degree == 0)
        if len(root_candidates) == 1:
            root = root_candidates[0]
            root_source = "inferred"
        elif len(root_candidates) == 0:
            issues.append("missing root binding: no zero-indegree node found")
        else:
            issues.append(f"ambiguous root binding: {', '.join(root_candidates)}")

    if not nodes and not edges:
        status = "empty" if not issues else "invalid"
    elif issues:
        status = "invalid"
    else:
        status = "valid"

    validation = {
        "schema": CAD_BOM_CONTRACT_SCHEMA,
        "status": status,
        "shape": shape,
        "raw_counts": {
            "nodes": len(raw_nodes),
            "edges": len(raw_edges),
        },
        "accepted_counts": {
            "nodes": len(nodes),
            "edges": accepted_edge_count,
        },
        "root": root,
        "root_source": root_source,
        "issues": issues,
    }
    return nodes, edges, root, validation


def _append_recovery_action(
    actions: List[Dict[str, str]],
    seen_codes: Set[str],
    *,
    code: str,
    label: str,
) -> None:
    if code in seen_codes:
        return
    actions.append({"code": code, "label": label})
    seen_codes.add(code)


def build_cad_bom_operator_summary(
    *,
    import_result: Optional[Dict[str, Any]],
    bom_payload: Optional[Dict[str, Any]] = None,
    has_artifact: bool,
) -> Dict[str, Any]:
    result = import_result if isinstance(import_result, dict) else {}
    validation = result.get("contract_validation")
    if not isinstance(validation, dict):
        _nodes, _edges, _root, validation = prepare_cad_bom_payload(bom_payload or {})

    issues = list(validation.get("issues") or [])
    errors = [str(err) for err in (result.get("errors") or []) if str(err).strip()]
    created_lines = int(result.get("created_lines") or 0)
    created_items = int(result.get("created_items") or 0)
    existing_items = int(result.get("existing_items") or 0)
    skipped_lines = int(result.get("skipped_lines") or 0)
    contract_status = str(validation.get("status") or "missing")
    actions: List[Dict[str, str]] = []
    action_codes: Set[str] = set()
    issue_codes: List[str] = []
    issue_code_set: Set[str] = set()

    def _append_issue_code(code: str) -> None:
        if code in issue_code_set:
            return
        issue_codes.append(code)
        issue_code_set.add(code)

    if not has_artifact and not result and not bom_payload:
        status = "missing"
        recoverable = True
        _append_issue_code("missing_bom_artifact")
        _append_recovery_action(
            actions,
            action_codes,
            code="request_cad_bom_import",
            label="Request CAD BOM extraction/import for this file.",
        )
    elif result.get("note") == "empty_bom" or contract_status == "empty":
        status = "empty"
        recoverable = True
        _append_issue_code("empty_bom")
        _append_recovery_action(
            actions,
            action_codes,
            code="verify_connector_bom_support",
            label="Verify that the connector and source assembly actually expose a BOM.",
        )
        _append_recovery_action(
            actions,
            action_codes,
            code="rerun_cad_bom_import",
            label="Re-run the CAD BOM import after confirming source assembly content.",
        )
    elif contract_status == "invalid" or errors or skipped_lines:
        status = "degraded"
        recoverable = True
        if contract_status == "invalid":
            _append_issue_code("contract_invalid")
    else:
        status = "ready"
        recoverable = False

    issue_text = " | ".join(issues)
    if "duplicate node id" in issue_text:
        _append_issue_code("duplicate_node_ids")
        _append_recovery_action(
            actions,
            action_codes,
            code="dedupe_node_ids",
            label="Deduplicate CAD BOM node identifiers before re-import.",
        )
    if (
        "root not found" in issue_text
        or "missing root binding" in issue_text
        or "ambiguous root binding" in issue_text
    ):
        _append_issue_code("root_binding_invalid")
        _append_recovery_action(
            actions,
            action_codes,
            code="repair_root_binding",
            label="Provide a single explicit root assembly node before re-import.",
        )
    if "parent not found" in issue_text or "child not found" in issue_text:
        _append_issue_code("edge_reference_missing")
        _append_recovery_action(
            actions,
            action_codes,
            code="repair_edge_references",
            label="Repair parent/child references so every BOM edge points to a known node.",
        )
    if errors or skipped_lines:
        if errors:
            _append_issue_code("import_errors")
        if skipped_lines:
            _append_issue_code("skipped_lines")
        _append_recovery_action(
            actions,
            action_codes,
            code="review_import_errors",
            label="Review import errors and skipped BOM lines before re-running the job.",
        )
    if has_artifact and (issues or errors):
        _append_recovery_action(
            actions,
            action_codes,
            code="inspect_raw_cad_bom",
            label="Download and inspect the raw CAD BOM artifact to confirm connector output.",
        )
    if recoverable and has_artifact:
        _append_recovery_action(
            actions,
            action_codes,
            code="rerun_cad_bom_import",
            label="Re-run the CAD BOM import after correcting contract or import issues.",
        )

    return {
        "status": status,
        "needs_operator_review": recoverable and status != "missing",
        "recoverable": recoverable,
        "has_artifact": has_artifact,
        "contract_status": contract_status,
        "issue_count": len(issues),
        "issue_codes": issue_codes,
        "error_count": len(errors),
        "created_items": created_items,
        "existing_items": existing_items,
        "created_lines": created_lines,
        "skipped_lines": skipped_lines,
        "raw_counts": validation.get("raw_counts") or {"nodes": 0, "edges": 0},
        "accepted_counts": validation.get("accepted_counts") or {"nodes": 0, "edges": 0},
        "root": validation.get("root"),
        "root_source": validation.get("root_source"),
        "recovery_actions": actions,
    }


def _find_existing_part_by_number(session: Session, item_number: Optional[str]) -> Optional[Item]:
    item_number = _normalize_text(item_number)
    if not item_number:
        return None
    existing = (
        session.query(Item)
        .filter(Item.item_type_id == "Part")
        .filter(_json_text(Item.properties["item_number"]) == item_number)
        .first()
    )
    if existing:
        return existing
    return (
        session.query(Item)
        .filter(Item.item_type_id == "Part")
        .filter(_json_text(Item.properties["drawing_no"]) == item_number)
        .first()
    )


def _cad_bom_node_item_number(node: Dict[str, Any]) -> Optional[str]:
    return _normalize_text(
        _extract_node_value(
            node,
            "part_number",
            "item_number",
            "number",
            "drawing_no",
            "id",
        )
    )


def _cad_bom_node_name(node: Dict[str, Any], matched_item: Optional[Item]) -> Optional[str]:
    if matched_item:
        props = matched_item.properties or {}
        return _normalize_text(props.get("name") or props.get("description"))
    return _normalize_text(_extract_node_value(node, "description", "name", "title"))


def _cad_bom_compare_result_to_rows(compare_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for entry in compare_result.get("added") or []:
        props = entry.get("properties") or {}
        rows.append(
            {
                "line_key": entry.get("line_key"),
                "parent_id": entry.get("parent_id"),
                "child_id": entry.get("child_id"),
                "status": "added",
                "quantity_before": None,
                "quantity_after": props.get("quantity"),
                "quantity_delta": props.get("quantity"),
                "uom_before": None,
                "uom_after": props.get("uom"),
                "severity": None,
                "change_fields": [],
            }
        )

    for entry in compare_result.get("removed") or []:
        props = entry.get("properties") or {}
        quantity = props.get("quantity")
        rows.append(
            {
                "line_key": entry.get("line_key"),
                "parent_id": entry.get("parent_id"),
                "child_id": entry.get("child_id"),
                "status": "removed",
                "quantity_before": quantity,
                "quantity_after": None,
                "quantity_delta": -float(quantity) if quantity is not None else None,
                "uom_before": props.get("uom"),
                "uom_after": None,
                "severity": None,
                "change_fields": [],
            }
        )

    for entry in compare_result.get("changed") or []:
        before = entry.get("before") or {}
        after = entry.get("after") or {}
        quantity_before = before.get("quantity")
        quantity_after = after.get("quantity")
        rows.append(
            {
                "line_key": entry.get("line_key"),
                "parent_id": entry.get("parent_id"),
                "child_id": entry.get("child_id"),
                "status": "changed",
                "quantity_before": quantity_before,
                "quantity_after": quantity_after,
                "quantity_delta": (
                    float(quantity_after) - float(quantity_before)
                    if quantity_before is not None and quantity_after is not None
                    else None
                ),
                "uom_before": before.get("uom"),
                "uom_after": after.get("uom"),
                "severity": entry.get("severity"),
                "change_fields": [
                    change.get("field")
                    for change in (entry.get("changes") or [])
                    if change.get("field")
                ],
            }
        )

    return rows


def _empty_cad_bom_mismatch_analysis(
    *,
    status: str,
    reason: Optional[str],
    analysis_scope: str,
    root_item_id: Optional[str],
    contract_status: Optional[str] = None,
) -> Dict[str, Any]:
    summary = {"total_ops": 0, "adds": 0, "removes": 0, "updates": 0, "risk_level": "none"}
    return {
        "status": status,
        "reason": reason,
        "analysis_scope": analysis_scope,
        "root_item_id": root_item_id,
        "line_key": "child_id_find_refdes",
        "recoverable": False,
        "contract_status": contract_status,
        "summary": summary,
        "compare_summary": {"added": 0, "removed": 0, "changed": 0},
        "grouped_counters": {"structure": 0, "quantity": 0, "uom": 0, "other": 0},
        "rows": [],
        "delta_preview": {"summary": summary},
        "issue_codes": [],
        "mismatch_groups": [],
        "recovery_actions": [],
        "live_bom": {},
    }


def _build_cad_bom_compare_tree(
    *,
    session: Session,
    root_item_id: str,
    bom_payload: Optional[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], str, Optional[str]]:
    root_item = session.get(Item, root_item_id)
    if not root_item:
        return None, {}, "unavailable", "item_not_found"

    nodes, edges, root_node_id, validation = prepare_cad_bom_payload(bom_payload or {})
    if not nodes or not root_node_id:
        if validation.get("status") == "empty":
            return None, validation, "unavailable", "empty_bom"
        if validation.get("status") == "invalid":
            return None, validation, "unavailable", "root_binding_invalid"
        return None, validation, "unavailable", "missing_bom_payload"

    nodes_by_id = {str(node.get("id")): node for node in nodes if node.get("id")}
    edges_by_parent: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
    for index, edge in enumerate(edges):
        parent_id = _normalize_text(_extract_node_value(edge, "parent", "from", "source"))
        child_id = _normalize_text(_extract_node_value(edge, "child", "to", "target"))
        if not parent_id or not child_id:
            continue
        if parent_id not in nodes_by_id or child_id not in nodes_by_id:
            continue
        edges_by_parent.setdefault(parent_id, []).append((index, edge))

    analysis_scope = "accepted_subset" if validation.get("status") == "invalid" else "full_payload"

    def _relationship_props(edge: Dict[str, Any]) -> Dict[str, Any]:
        props: Dict[str, Any] = {
            "quantity": _parse_quantity(_extract_node_value(edge, "quantity", "qty"), default=1.0),
            "uom": _normalize_text(_extract_node_value(edge, "uom")) or "EA",
        }
        find_num = _normalize_text(_extract_node_value(edge, "find_num"))
        if find_num:
            props["find_num"] = find_num
        refdes = _normalize_refdes(_extract_node_value(edge, "refdes"))
        if refdes:
            props["refdes"] = refdes
        return props

    def _build_node(node_id: str, path: Set[str]) -> Dict[str, Any]:
        node = nodes_by_id[node_id]
        matched_item = _find_existing_part_by_number(session, _cad_bom_node_item_number(node))
        if node_id == root_node_id:
            matched_item = root_item

        item_number = (
            _normalize_text((matched_item.properties or {}).get("item_number"))
            if matched_item
            else _cad_bom_node_item_number(node)
        )
        item_name = _cad_bom_node_name(node, matched_item)
        tree_node = {
            "id": matched_item.id if matched_item else f"cad-node::{node_id}",
            "config_id": matched_item.config_id if matched_item else f"cad-config::{node_id}",
            "item_number": item_number,
            "name": item_name,
            "children": [],
        }

        if node_id in path:
            return tree_node

        next_path = set(path)
        next_path.add(node_id)
        for index, edge in edges_by_parent.get(node_id, []):
            child_id = _normalize_text(_extract_node_value(edge, "child", "to", "target"))
            if not child_id or child_id not in nodes_by_id:
                continue
            tree_node["children"].append(
                {
                    "relationship": {
                        "id": f"cad-bom::{node_id}::{child_id}::{index}",
                        "properties": _relationship_props(edge),
                    },
                    "child": _build_node(child_id, next_path),
                }
            )
        return tree_node

    return _build_node(root_node_id, set()), validation, analysis_scope, None


def build_cad_bom_mismatch_analysis(
    *,
    session: Session,
    root_item_id: Optional[str],
    bom_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not _normalize_text(root_item_id):
        return _empty_cad_bom_mismatch_analysis(
            status="unresolved",
            reason="item_binding_missing",
            analysis_scope="unavailable",
            root_item_id=root_item_id,
        )

    cad_tree, validation, analysis_scope, failure_reason = _build_cad_bom_compare_tree(
        session=session,
        root_item_id=str(root_item_id),
        bom_payload=bom_payload,
    )
    if not cad_tree:
        status = "missing" if failure_reason == "empty_bom" else "unresolved"
        return _empty_cad_bom_mismatch_analysis(
            status=status,
            reason=failure_reason or "cad_bom_unavailable",
            analysis_scope=analysis_scope,
            root_item_id=root_item_id,
            contract_status=validation.get("status") if isinstance(validation, dict) else None,
        )

    bom_service = BOMService(session)
    live_tree = bom_service.get_bom_structure(str(root_item_id), levels=-1)
    compare_result = bom_service.compare_bom_trees(
        live_tree,
        cad_tree,
        include_relationship_props=["quantity", "uom", "find_num", "refdes"],
        line_key="child_id_find_refdes",
        aggregate_quantities=False,
    )
    delta_preview = bom_service.build_delta_preview(compare_result)
    summary = delta_preview.get("summary") or {}
    compare_summary = compare_result.get("summary") or {}
    rows = _cad_bom_compare_result_to_rows(compare_result)
    quantity_updates = 0
    uom_updates = 0
    other_updates = 0
    for entry in compare_result.get("changed") or []:
        fields = {
            str(change.get("field"))
            for change in (entry.get("changes") or [])
            if change.get("field")
        }
        if "quantity" in fields:
            quantity_updates += 1
        if "uom" in fields:
            uom_updates += 1
        if fields - {"quantity", "uom"}:
            other_updates += 1

    issue_codes: List[str] = []
    recovery_actions: List[Dict[str, str]] = []
    seen_action_codes: Set[str] = set()
    mismatch_groups: List[str] = []
    if summary.get("adds") or summary.get("removes"):
        if summary.get("adds"):
            mismatch_groups.append("missing_in_live_bom")
        if summary.get("removes"):
            mismatch_groups.append("extra_in_live_bom")
        issue_codes.append("live_bom_structure_mismatch")
        _append_recovery_action(
            recovery_actions,
            seen_action_codes,
            code="review_live_bom_structure",
            label="Review structural drift between current live BOM and imported CAD BOM.",
        )
    if summary.get("updates"):
        mismatch_groups.append("line_value_mismatch")
        issue_codes.append("live_bom_quantity_mismatch")
        _append_recovery_action(
            recovery_actions,
            seen_action_codes,
            code="review_live_bom_quantities",
            label="Review quantity or UOM drift between current live BOM and imported CAD BOM.",
        )
    if issue_codes:
        _append_recovery_action(
            recovery_actions,
            seen_action_codes,
            code="open_cad_bom_mismatch_surface",
            label="Open the CAD BOM mismatch surface and inspect grouped mismatch counters.",
        )
    if summary.get("total_ops"):
        _append_recovery_action(
            recovery_actions,
            seen_action_codes,
            code="export_mismatch_proof_bundle",
            label="Export the CAD BOM proof bundle before applying recovery actions.",
        )
        _append_recovery_action(
            recovery_actions,
            seen_action_codes,
            code="rerun_cad_bom_import_after_drift_review",
            label="Re-run CAD BOM import only after live BOM drift is reviewed and accepted.",
        )

    return {
        "status": "match" if int(summary.get("total_ops") or 0) == 0 else "mismatch",
        "reason": None,
        "analysis_scope": analysis_scope,
        "root_item_id": root_item_id,
        "line_key": "child_id_find_refdes",
        "recoverable": int(summary.get("total_ops") or 0) > 0,
        "contract_status": validation.get("status"),
        "summary": summary,
        "compare_summary": compare_summary,
        "grouped_counters": {
            "structure": int(summary.get("adds") or 0) + int(summary.get("removes") or 0),
            "quantity": quantity_updates,
            "uom": uom_updates,
            "other": other_updates,
        },
        "rows": rows,
        "delta_preview": delta_preview,
        "issue_codes": issue_codes,
        "mismatch_groups": mismatch_groups,
        "recovery_actions": recovery_actions,
        "live_bom": live_tree,
    }


class CadBomImportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.bom_service = BOMService(session)

    def import_bom(
        self,
        *,
        root_item_id: str,
        bom_payload: Dict[str, Any],
        user_id: Optional[int] = None,
        roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not root_item_id:
            raise ValueError("Missing root_item_id for BOM import")
        root_item = self.session.get(Item, root_item_id)
        if not root_item:
            raise ValueError(f"Root item not found: {root_item_id}")

        part_type = self.session.get(ItemType, "Part")
        if not part_type:
            raise ValueError("Part ItemType not found")

        nodes, edges, root_node_id, contract_validation = prepare_cad_bom_payload(
            bom_payload or {}
        )
        if contract_validation["status"] == "empty":
            return {
                "ok": True,
                "created_items": 0,
                "existing_items": 0,
                "created_lines": 0,
                "skipped_lines": 0,
                "errors": [],
                "note": "empty_bom",
                "contract_validation": contract_validation,
            }

        prop_names = {prop.name for prop in (part_type.properties or [])}
        cad_synced = [prop for prop in (part_type.properties or []) if prop.is_cad_synced]
        root_permission = root_item.permission_id

        def _find_existing(item_number: str) -> Optional[Item]:
            if not item_number:
                return None
            existing = (
                self.session.query(Item)
                .filter(Item.item_type_id == "Part")
                .filter(_json_text(Item.properties["item_number"]) == item_number)
                .first()
            )
            if existing:
                return existing
            return (
                self.session.query(Item)
                .filter(Item.item_type_id == "Part")
                .filter(_json_text(Item.properties["drawing_no"]) == item_number)
                .first()
            )

        def _build_properties(node: Dict[str, Any]) -> Dict[str, Any]:
            attrs = normalize_cad_attributes(node)
            props: Dict[str, Any] = {}
            item_number = _normalize_text(
                _extract_node_value(
                    attrs,
                    "part_number",
                    "item_number",
                    "number",
                    "drawing_no",
                    "id",
                )
            )
            description = _normalize_text(
                _extract_node_value(attrs, "description", "name", "title")
            )
            revision = _normalize_text(_extract_node_value(attrs, "revision", "rev"))
            material = _normalize_text(_extract_node_value(attrs, "material"))
            weight = attrs.get("weight")

            if item_number and "item_number" in prop_names:
                props["item_number"] = item_number
            if description:
                if "description" in prop_names:
                    props["description"] = description
                if "name" in prop_names:
                    props.setdefault("name", description)
            if not props.get("name") and "name" in prop_names:
                props["name"] = item_number or description or "CAD Part"
            if revision and "revision" in prop_names:
                props["revision"] = revision
            if material and "material" in prop_names:
                props["material"] = material
            if weight is not None and "weight" in prop_names:
                props["weight"] = weight

            for prop in cad_synced:
                if prop.name in props:
                    continue
                cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
                value = _extract_node_value(attrs, cad_key)
                if value is not None:
                    props[prop.name] = value

            return props

        node_map: Dict[str, str] = {}
        created_items = 0
        existing_items = 0
        errors: List[str] = []

        for node in nodes:
            node_id = _normalize_text(
                _extract_node_value(
                    node, "id", "uid", "node_id", "part_number", "item_number", "number"
                )
            ) or ""
            if not node_id:
                continue

            if root_node_id and node_id == root_node_id:
                node_map[node_id] = root_item_id
                continue

            props = _build_properties(node)
            item_number = _normalize_text(props.get("item_number")) if props else None
            existing = _find_existing(item_number) if item_number else None
            if existing:
                node_map[node_id] = existing.id
                existing_items += 1
                continue

            item = Item(
                id=str(uuid.uuid4()),
                item_type_id="Part",
                config_id=str(uuid.uuid4()),
                generation=1,
                is_current=True,
                state="Active",
                properties=props,
                created_by_id=user_id,
                owner_id=user_id,
                created_at=datetime.utcnow(),
                permission_id=root_permission,
            )
            self.session.add(item)
            self.session.flush()
            node_map[node_id] = item.id
            created_items += 1

        created_lines = 0
        skipped_lines = 0

        for edge in edges:
            parent_id = _normalize_text(_extract_node_value(edge, "parent", "from", "source"))
            child_id = _normalize_text(_extract_node_value(edge, "child", "to", "target"))
            if not parent_id or not child_id:
                skipped_lines += 1
                continue
            parent_item_id = node_map.get(parent_id, root_item_id if parent_id == root_node_id else None)
            child_item_id = node_map.get(child_id)
            if not parent_item_id or not child_item_id:
                skipped_lines += 1
                continue

            qty = _parse_quantity(_extract_node_value(edge, "quantity", "qty", "count"), default=1.0)
            uom = _normalize_text(_extract_node_value(edge, "uom", "unit")) or "EA"
            find_num = _normalize_text(_extract_node_value(edge, "find_num", "findno", "position"))
            refdes = _normalize_refdes(_extract_node_value(edge, "refdes", "ref_des"))

            try:
                self.bom_service.add_child(
                    parent_item_id,
                    child_item_id,
                    user_id=user_id,
                    quantity=qty,
                    uom=uom,
                    find_num=find_num,
                    refdes=refdes,
                )
                created_lines += 1
            except Exception as exc:
                skipped_lines += 1
                errors.append(str(exc))

        return {
            "ok": True,
            "created_items": created_items,
            "existing_items": existing_items,
            "created_lines": created_lines,
            "skipped_lines": skipped_lines,
            "errors": errors,
            "contract_validation": contract_validation,
        }
