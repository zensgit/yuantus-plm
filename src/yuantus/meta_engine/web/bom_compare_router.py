from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
import io
import json
import threading
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from yuantus.database import get_db
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.api.dependencies.auth import CurrentUser, get_current_user

bom_compare_router = APIRouter(prefix="/bom", tags=["BOM"])


# ============================================================================
# BOM Compare API - Response Models
# ============================================================================


class BOMCompareSummary(BaseModel):
    """Summary counts for BOM compare."""

    added: int
    removed: int
    changed: int
    changed_major: int = 0
    changed_minor: int = 0
    changed_info: int = 0


class BOMCompareEntry(BaseModel):
    """Entry for added/removed relationships."""

    parent_id: Optional[str] = None
    child_id: Optional[str] = None
    relationship_id: Optional[str] = None
    line_key: Optional[str] = None
    parent_config_id: Optional[str] = None
    child_config_id: Optional[str] = None
    level: Optional[int] = None
    path: Optional[List[Dict[str, Any]]] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    line: Dict[str, Any] = Field(default_factory=dict, description="Standardized BOM line fields")
    line_normalized: Dict[str, Any] = Field(
        default_factory=dict, description="Normalized line fields for comparisons"
    )
    parent: Optional[Dict[str, Any]] = None
    child: Optional[Dict[str, Any]] = None
    parent_number: Optional[str] = None
    parent_name: Optional[str] = None
    child_number: Optional[str] = None
    child_name: Optional[str] = None


class BOMCompareFieldDiff(BaseModel):
    """Field-level diff for changed BOM line properties."""

    field: str
    left: Any = None
    right: Any = None
    normalized_left: Any = None
    normalized_right: Any = None
    severity: str = "info"


class BOMCompareChangedEntry(BaseModel):
    """Entry for changed relationships."""

    parent_id: Optional[str] = None
    child_id: Optional[str] = None
    relationship_id: Optional[str] = None
    line_key: Optional[str] = None
    parent_config_id: Optional[str] = None
    child_config_id: Optional[str] = None
    level: Optional[int] = None
    path: Optional[List[Dict[str, Any]]] = None
    before: Dict[str, Any] = Field(default_factory=dict)
    after: Dict[str, Any] = Field(default_factory=dict)
    before_line: Dict[str, Any] = Field(default_factory=dict)
    after_line: Dict[str, Any] = Field(default_factory=dict)
    before_normalized: Dict[str, Any] = Field(default_factory=dict)
    after_normalized: Dict[str, Any] = Field(default_factory=dict)
    changes: List[BOMCompareFieldDiff] = Field(default_factory=list)
    severity: Optional[str] = None
    parent: Optional[Dict[str, Any]] = None
    child: Optional[Dict[str, Any]] = None
    parent_number: Optional[str] = None
    parent_name: Optional[str] = None
    child_number: Optional[str] = None
    child_name: Optional[str] = None


class BOMCompareResponse(BaseModel):
    """Response for BOM compare."""

    summary: BOMCompareSummary
    added: List[BOMCompareEntry]
    removed: List[BOMCompareEntry]
    changed: List[BOMCompareChangedEntry]


class BOMCompareFieldSpec(BaseModel):
    """Field metadata for BOM compare diff."""

    field: str
    severity: str
    normalized: str
    description: str


class BOMCompareModeSpec(BaseModel):
    """Compare mode specification."""

    mode: str
    line_key: Optional[str] = None
    include_relationship_props: List[str] = Field(default_factory=list)
    aggregate_quantities: bool = False
    aliases: List[str] = Field(default_factory=list)
    description: str


class BOMCompareSchemaResponse(BaseModel):
    """Schema metadata for BOM compare."""

    line_fields: List[BOMCompareFieldSpec]
    compare_modes: List[BOMCompareModeSpec]
    line_key_options: List[str]
    defaults: Dict[str, Any]


# ============================================================================
# BOM Compare Summarized - Module-level snapshot store
# ============================================================================

_BOM_COMPARE_SUMMARIZED_SNAPSHOTS: List[Dict[str, Any]] = []
_BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK = threading.Lock()


# ============================================================================
# Helpers: transform compare result -> summarized rows
# ============================================================================


def _compare_result_to_summarized_rows(result: Dict[str, Any]) -> Dict[str, Any]:
    """Transform a raw compare result into a flat row list with quantity deltas."""
    rows: List[Dict[str, Any]] = []
    quantity_delta_total = 0.0

    for item in result.get("added", []):
        props = item.get("properties") or {}
        qty = props.get("quantity")
        qty_f = float(qty) if qty is not None else 0.0
        rows.append({
            "line_key": item.get("line_key"),
            "parent_id": item.get("parent_id"),
            "child_id": item.get("child_id"),
            "status": "added",
            "quantity_before": None,
            "quantity_after": qty_f if qty is not None else None,
            "quantity_delta": qty_f,
            "uom_before": None,
            "uom_after": props.get("uom"),
            "relationship_id_before": None,
            "relationship_id_after": item.get("relationship_id"),
            "severity": None,
            "change_fields": [],
        })
        quantity_delta_total += qty_f

    for item in result.get("removed", []):
        props = item.get("properties") or {}
        qty = props.get("quantity")
        qty_f = float(qty) if qty is not None else 0.0
        rows.append({
            "line_key": item.get("line_key"),
            "parent_id": item.get("parent_id"),
            "child_id": item.get("child_id"),
            "status": "removed",
            "quantity_before": qty_f if qty is not None else None,
            "quantity_after": None,
            "quantity_delta": -qty_f,
            "uom_before": props.get("uom"),
            "uom_after": None,
            "relationship_id_before": item.get("relationship_id"),
            "relationship_id_after": None,
            "severity": None,
            "change_fields": [],
        })
        quantity_delta_total += -qty_f

    for item in result.get("changed", []):
        before = item.get("before") or {}
        after = item.get("after") or {}
        qty_before = before.get("quantity")
        qty_after = after.get("quantity")
        qty_b = float(qty_before) if qty_before is not None else 0.0
        qty_a = float(qty_after) if qty_after is not None else 0.0
        change_fields = [c.get("field") for c in (item.get("changes") or []) if c.get("field")]
        rows.append({
            "line_key": item.get("line_key"),
            "parent_id": item.get("parent_id"),
            "child_id": item.get("child_id"),
            "status": "changed",
            "quantity_before": qty_b if qty_before is not None else None,
            "quantity_after": qty_a if qty_after is not None else None,
            "quantity_delta": qty_a - qty_b,
            "uom_before": before.get("uom"),
            "uom_after": after.get("uom"),
            "relationship_id_before": item.get("relationship_id"),
            "relationship_id_after": item.get("relationship_id"),
            "severity": item.get("severity"),
            "change_fields": change_fields,
        })
        quantity_delta_total += qty_a - qty_b

    summary = dict(result.get("summary", {}))
    summary["total"] = len(rows)
    summary["total_rows"] = len(rows)
    summary["quantity_delta_total"] = quantity_delta_total

    return {"summary": summary, "rows": rows}


_SUMMARIZED_CSV_HEADERS = (
    "line_key,parent_id,child_id,status,quantity_before,quantity_after,"
    "quantity_delta,uom_before,uom_after,relationship_id_before,relationship_id_after,"
    "severity,change_fields"
)

_SUMMARIZED_MD_HEADERS = (
    "| line_key | parent_id | child_id | status | quantity_before | quantity_after | "
    "quantity_delta | uom_before | uom_after | relationship_id_before | "
    "relationship_id_after | severity | change_fields |"
)


def _rows_to_csv(rows: List[Dict[str, Any]]) -> str:
    lines = [_SUMMARIZED_CSV_HEADERS]
    for r in rows:
        def _v(val):
            if val is None:
                return ""
            if isinstance(val, list):
                return ";".join(str(x) for x in val)
            if isinstance(val, float):
                return str(val)
            return str(val)

        lines.append(",".join([
            _v(r.get("line_key")), _v(r.get("parent_id")), _v(r.get("child_id")),
            _v(r.get("status")), _v(r.get("quantity_before")), _v(r.get("quantity_after")),
            _v(r.get("quantity_delta")), _v(r.get("uom_before")), _v(r.get("uom_after")),
            _v(r.get("relationship_id_before")), _v(r.get("relationship_id_after")),
            _v(r.get("severity")), _v(r.get("change_fields")),
        ]))
    return "\n".join(lines)


def _rows_to_markdown(rows: List[Dict[str, Any]], title: str = "BOM Compare Summarized") -> str:
    sep = "| " + " | ".join(["---"] * 13) + " |"
    lines = [f"# {title}", "", _SUMMARIZED_MD_HEADERS, sep]
    for r in rows:
        def _v(val):
            if val is None:
                return ""
            if isinstance(val, list):
                return ";".join(str(x) for x in val)
            return str(val)

        lines.append("| " + " | ".join([
            _v(r.get("line_key")), _v(r.get("parent_id")), _v(r.get("child_id")),
            _v(r.get("status")), _v(r.get("quantity_before")), _v(r.get("quantity_after")),
            _v(r.get("quantity_delta")), _v(r.get("uom_before")), _v(r.get("uom_after")),
            _v(r.get("relationship_id_before")), _v(r.get("relationship_id_after")),
            _v(r.get("severity")), _v(r.get("change_fields")),
        ]) + " |")
    return "\n".join(lines)


def _validate_export_format(fmt: str) -> None:
    if fmt not in {"json", "csv", "md"}:
        raise HTTPException(status_code=400, detail="export_format must be json, csv or md")


def _find_snapshot(snapshot_id: str) -> Dict[str, Any]:
    with _BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        for s in _BOM_COMPARE_SUMMARIZED_SNAPSHOTS:
            if s["snapshot_id"] == snapshot_id:
                return s
    raise HTTPException(status_code=404, detail=f"snapshot {snapshot_id} not found")


# ============================================================================
# Snapshot diff helpers
# ============================================================================


def _diff_snapshot_rows(
    left_rows: List[Dict[str, Any]],
    right_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare two lists of summarized rows and return differences."""
    left_by_key = {r["line_key"]: r for r in left_rows}
    right_by_key = {r["line_key"]: r for r in right_rows}
    all_keys = list(dict.fromkeys(list(left_by_key.keys()) + list(right_by_key.keys())))

    differences: List[Dict[str, Any]] = []
    added = 0
    removed = 0
    changed = 0

    compare_fields = [
        "quantity_before", "quantity_after", "quantity_delta",
        "uom_before", "uom_after", "status", "severity",
        "relationship_id_before", "relationship_id_after",
    ]

    for key in all_keys:
        left_row = left_by_key.get(key)
        right_row = right_by_key.get(key)
        if left_row and not right_row:
            removed += 1
            differences.append({
                "change_type": "removed",
                "row_key": key,
                "line_key": key,
                "parent_id": left_row.get("parent_id"),
                "child_id": left_row.get("child_id"),
                "status": left_row.get("status"),
                "changed_fields": [],
            })
        elif right_row and not left_row:
            added += 1
            differences.append({
                "change_type": "added",
                "row_key": key,
                "line_key": key,
                "parent_id": right_row.get("parent_id"),
                "child_id": right_row.get("child_id"),
                "status": right_row.get("status"),
                "changed_fields": [],
            })
        else:
            changed_fields = [
                f for f in compare_fields if left_row.get(f) != right_row.get(f)
            ]
            if changed_fields:
                changed += 1
                differences.append({
                    "change_type": "changed",
                    "row_key": key,
                    "line_key": key,
                    "parent_id": right_row.get("parent_id"),
                    "child_id": right_row.get("child_id"),
                    "status": right_row.get("status"),
                    "changed_fields": changed_fields,
                })

    return {
        "summary": {
            "total_differences": len(differences),
            "added": added,
            "removed": removed,
            "changed": changed,
            "left_rows": len(left_rows),
            "right_rows": len(right_rows),
        },
        "differences": differences,
    }


_DIFF_CSV_HEADERS = "change_type,row_key,line_key,parent_id,child_id,status,changed_fields"


def _diff_to_csv(diff_result: Dict[str, Any]) -> str:
    lines = [_DIFF_CSV_HEADERS]
    for d in diff_result.get("differences", []):
        cf = ";".join(d.get("changed_fields", []))
        lines.append(",".join([
            str(d.get("change_type", "")),
            str(d.get("row_key", "")),
            str(d.get("line_key", "")),
            str(d.get("parent_id", "")),
            str(d.get("child_id", "")),
            str(d.get("status", "")),
            cf,
        ]))
    return "\n".join(lines)


def _diff_to_markdown(diff_result: Dict[str, Any], title: str) -> str:
    sep = "| " + " | ".join(["---"] * 7) + " |"
    header = "| change_type | row_key | line_key | parent_id | child_id | status | changed_fields |"
    lines = [f"# {title}", "", header, sep]
    for d in diff_result.get("differences", []):
        cf = ";".join(d.get("changed_fields", []))
        lines.append("| " + " | ".join([
            str(d.get("change_type", "")),
            str(d.get("row_key", "")),
            str(d.get("line_key", "")),
            str(d.get("parent_id", "")),
            str(d.get("child_id", "")),
            str(d.get("status", "")),
            cf,
        ]) + " |")
    return "\n".join(lines)


def _export_diff(diff_result: Dict[str, Any], export_format: str, filename_base: str):
    _validate_export_format(export_format)
    if export_format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(diff_result, indent=2, default=str).encode()),
            media_type="application/json",
            headers={"content-disposition": f'attachment; filename="{filename_base}.json"'},
        )
    if export_format == "csv":
        return StreamingResponse(
            io.BytesIO(_diff_to_csv(diff_result).encode()),
            media_type="text/csv",
            headers={"content-disposition": f'attachment; filename="{filename_base}.csv"'},
        )
    md = _diff_to_markdown(diff_result, "BOM Summarized Snapshot Diff")
    return StreamingResponse(
        io.BytesIO(md.encode()),
        media_type="text/markdown",
        headers={"content-disposition": f'attachment; filename="{filename_base}.md"'},
    )


# ============================================================================
# BOM Compare Summarized - Request Models
# ============================================================================


class SnapshotCreateRequest(BaseModel):
    left_type: str = "item"
    left_id: str
    right_type: str = "item"
    right_id: str
    max_levels: int = 10
    effective_at: Optional[datetime] = None
    include_child_fields: bool = False
    include_relationship_props: List[str] = Field(default_factory=list)
    line_key: str = "child_config"
    include_substitutes: bool = False
    include_effectivity: bool = False
    name: str = ""
    note: str = ""


# ============================================================================
# BOM Compare Handlers - preserve source declaration order
# (Static `/snapshots/compare` routes appear before `/snapshots/{snapshot_id}`
# dynamic routes so FastAPI does not capture "compare" as a snapshot id.)
# ============================================================================


@bom_compare_router.get(
    "/compare/schema",
    response_model=BOMCompareSchemaResponse,
    summary="Get BOM compare schema",
    description="Returns field-level mapping, severity, and compare mode options.",
)
async def get_bom_compare_schema(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    return BOMService.compare_schema()


@bom_compare_router.get(
    "/compare",
    response_model=BOMCompareResponse,
    summary="Compare two BOM trees",
    description="Compare BOM structures between two items or versions.",
)
async def compare_bom(
    left_type: str = Query(..., description="item or version"),
    left_id: str = Query(..., description="Left item/version ID"),
    right_type: str = Query(..., description="item or version"),
    right_id: str = Query(..., description="Right item/version ID"),
    max_levels: int = Query(10, description="Explosion depth (-1 for unlimited)"),
    effective_at: Optional[datetime] = Query(None, description="Effectivity filter date"),
    include_child_fields: bool = Query(False, description="Include parent/child fields"),
    include_relationship_props: Optional[List[str]] = Query(
        None, description="Comma-separated relationship property whitelist"
    ),
    line_key: str = Query(
        "child_config",
        description=(
            "Line key strategy: child_config, child_id, relationship_id, "
            "child_config_find_num, child_config_refdes, child_config_find_refdes, "
            "child_id_find_num, child_id_refdes, child_id_find_refdes, "
            "child_config_find_num_qty, child_id_find_num_qty, line_full"
        ),
    ),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    include_substitutes: bool = Query(False, description="Include substitutes in compare"),
    include_effectivity: bool = Query(False, description="Include effectivity records in compare"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if max_levels < -1:
        raise HTTPException(status_code=400, detail="max_levels must be >= -1")

    left_type = left_type.strip().lower()
    right_type = right_type.strip().lower()
    if left_type not in {"item", "version"} or right_type not in {"item", "version"}:
        raise HTTPException(
            status_code=400,
            detail="left_type/right_type must be 'item' or 'version'",
        )

    def normalize_props(values: Optional[List[str]]) -> Optional[List[str]]:
        if not values:
            return None
        flattened: List[str] = []
        for raw in values:
            if raw is None:
                continue
            for part in str(raw).split(","):
                part = part.strip()
                if part:
                    flattened.append(part)
        return flattened or None

    aggregate_quantities = False

    try:
        mode_line_key, mode_props, mode_aggregate = BOMService.resolve_compare_mode(
            compare_mode
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if mode_line_key:
        line_key = mode_line_key
        include_props = mode_props
        aggregate_quantities = mode_aggregate
    else:
        include_props = normalize_props(include_relationship_props)

    perm = MetaPermissionService(db)
    if not perm.check_permission(
        "Part BOM",
        AMLAction.get,
        user_id=str(user.id),
        user_roles=user.roles,
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = BOMService(db)

    def resolve_tree(ref_type: str, ref_id: str) -> Dict[str, Any]:
        if ref_type == "item":
            item = db.get(Item, ref_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"Item {ref_id} not found")
            if not perm.check_permission(
                item.item_type_id,
                AMLAction.get,
                user_id=str(user.id),
                user_roles=user.roles,
            ):
                raise HTTPException(status_code=403, detail="Permission denied")
            return service.get_bom_structure(
                ref_id,
                levels=max_levels,
                effective_date=effective_at,
                include_substitutes=include_substitutes,
            )

        from yuantus.meta_engine.version.models import ItemVersion

        version = db.get(ItemVersion, ref_id)
        if not version:
            raise HTTPException(status_code=404, detail=f"Version {ref_id} not found")
        item = db.get(Item, version.item_id)
        if not item:
            raise HTTPException(
                status_code=404, detail=f"Item {version.item_id} not found"
            )
        if not perm.check_permission(
            item.item_type_id,
            AMLAction.get,
            user_id=str(user.id),
            user_roles=user.roles,
        ):
            raise HTTPException(status_code=403, detail="Permission denied")

        if effective_at:
            return service.get_bom_structure(
                item.id,
                levels=max_levels,
                effective_date=effective_at,
                include_substitutes=include_substitutes,
            )
        try:
            return service.get_bom_for_version(
                ref_id,
                levels=max_levels,
                include_substitutes=include_substitutes,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    def normalize_root(tree: Dict[str, Any]) -> Dict[str, Any]:
        if not tree:
            return tree
        normalized = dict(tree)
        normalized["config_id"] = "ROOT"
        return normalized

    left_tree = normalize_root(resolve_tree(left_type, left_id))
    right_tree = normalize_root(resolve_tree(right_type, right_id))

    return service.compare_bom_trees(
        left_tree,
        right_tree,
        include_relationship_props=include_props,
        include_child_fields=include_child_fields,
        line_key=line_key,
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        aggregate_quantities=aggregate_quantities,
    )


@bom_compare_router.get(
    "/compare/delta/preview",
    summary="Preview BOM delta patch",
    description="Generate read-only delta operations from BOM compare result.",
)
async def compare_bom_delta_preview(
    left_type: str = Query(..., description="item or version"),
    left_id: str = Query(..., description="Left item/version ID"),
    right_type: str = Query(..., description="item or version"),
    right_id: str = Query(..., description="Right item/version ID"),
    max_levels: int = Query(10, description="Explosion depth (-1 for unlimited)"),
    effective_at: Optional[datetime] = Query(None, description="Effectivity filter date"),
    include_child_fields: bool = Query(False, description="Include parent/child fields"),
    include_relationship_props: Optional[List[str]] = Query(
        None, description="Comma-separated relationship property whitelist"
    ),
    line_key: str = Query("child_config", description="Line key strategy"),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    fields: Optional[List[str]] = Query(
        None,
        description=(
            "Optional exported fields: op,line_key,parent_id,child_id,relationship_id,"
            "severity,risk_level,change_count,field,before,after,properties"
        ),
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    compare_result = await compare_bom(
        left_type=left_type,
        left_id=left_id,
        right_type=right_type,
        right_id=right_id,
        max_levels=max_levels,
        effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key,
        compare_mode=compare_mode,
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user,
        db=db,
    )
    service = BOMService(db)
    delta = service.build_delta_preview(compare_result)
    delta["compare_summary"] = compare_result.get("summary") or {}
    try:
        return service.filter_delta_preview_fields(delta, fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@bom_compare_router.get(
    "/compare/delta/export",
    summary="Export BOM delta patch",
    description="Export delta preview as json, csv or md.",
)
async def compare_bom_delta_export(
    left_type: str = Query(..., description="item or version"),
    left_id: str = Query(..., description="Left item/version ID"),
    right_type: str = Query(..., description="item or version"),
    right_id: str = Query(..., description="Right item/version ID"),
    max_levels: int = Query(10, description="Explosion depth (-1 for unlimited)"),
    effective_at: Optional[datetime] = Query(None, description="Effectivity filter date"),
    include_child_fields: bool = Query(False, description="Include parent/child fields"),
    include_relationship_props: Optional[List[str]] = Query(
        None, description="Comma-separated relationship property whitelist"
    ),
    line_key: str = Query("child_config", description="Line key strategy"),
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    fields: Optional[List[str]] = Query(
        None,
        description=(
            "Optional exported fields: op,line_key,parent_id,child_id,relationship_id,"
            "severity,risk_level,change_count,field,before,after,properties"
        ),
    ),
    export_format: str = Query("json", description="json|csv|md"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    compare_result = await compare_bom(
        left_type=left_type,
        left_id=left_id,
        right_type=right_type,
        right_id=right_id,
        max_levels=max_levels,
        effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key,
        compare_mode=compare_mode,
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user,
        db=db,
    )
    service = BOMService(db)
    delta = service.build_delta_preview(compare_result)
    delta["compare_summary"] = compare_result.get("summary") or {}
    try:
        delta_filtered = service.filter_delta_preview_fields(delta, fields)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    normalized = (export_format or "json").strip().lower()
    if normalized == "json":
        payload = json.dumps(delta_filtered, ensure_ascii=False, indent=2).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(payload),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="bom-delta-preview.json"'},
        )
    if normalized == "csv":
        csv_text = service.export_delta_csv(delta, fields=fields)
        return StreamingResponse(
            io.BytesIO(csv_text.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="bom-delta-preview.csv"'},
        )
    if normalized == "md":
        md_text = service.export_delta_markdown(delta_filtered, fields=fields)
        return StreamingResponse(
            io.BytesIO(md_text.encode("utf-8")),
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="bom-delta-preview.md"'},
        )
    raise HTTPException(status_code=400, detail="export_format must be json, csv or md")


@bom_compare_router.get(
    "/compare/summarized",
    summary="Compare two BOM trees in summarized row format",
)
async def compare_bom_summarized(
    left_type: str = Query(...),
    left_id: str = Query(...),
    right_type: str = Query(...),
    right_id: str = Query(...),
    max_levels: int = Query(10),
    effective_at: Optional[datetime] = Query(None),
    include_child_fields: bool = Query(False),
    include_relationship_props: Optional[List[str]] = Query(None),
    line_key: str = Query("child_config"),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await compare_bom(
        left_type=left_type, left_id=left_id,
        right_type=right_type, right_id=right_id,
        max_levels=max_levels, effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key, compare_mode="summarized",
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user, db=db,
    )
    return _compare_result_to_summarized_rows(result)


@bom_compare_router.get(
    "/compare/summarized/export",
    summary="Export summarized BOM comparison",
)
async def compare_bom_summarized_export(
    left_type: str = Query(...),
    left_id: str = Query(...),
    right_type: str = Query(...),
    right_id: str = Query(...),
    max_levels: int = Query(10),
    effective_at: Optional[datetime] = Query(None),
    include_child_fields: bool = Query(False),
    include_relationship_props: Optional[List[str]] = Query(None),
    line_key: str = Query("child_config"),
    include_substitutes: bool = Query(False),
    include_effectivity: bool = Query(False),
    export_format: str = Query("csv"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_export_format(export_format)
    result = await compare_bom(
        left_type=left_type, left_id=left_id,
        right_type=right_type, right_id=right_id,
        max_levels=max_levels, effective_at=effective_at,
        include_child_fields=include_child_fields,
        include_relationship_props=include_relationship_props,
        line_key=line_key, compare_mode="summarized",
        include_substitutes=include_substitutes,
        include_effectivity=include_effectivity,
        user=user, db=db,
    )
    payload = _compare_result_to_summarized_rows(result)
    rows = payload["rows"]

    if export_format == "json":
        return JSONResponse(content=payload)
    if export_format == "csv":
        return StreamingResponse(
            io.BytesIO(_rows_to_csv(rows).encode()),
            media_type="text/csv",
            headers={"content-disposition": 'attachment; filename="bom-compare-summarized.csv"'},
        )
    md = _rows_to_markdown(rows)
    return StreamingResponse(
        io.BytesIO(md.encode()),
        media_type="text/markdown",
        headers={"content-disposition": 'attachment; filename="bom-compare-summarized.md"'},
    )


@bom_compare_router.post(
    "/compare/summarized/snapshots",
    summary="Create a summarized BOM comparison snapshot",
)
async def create_bom_summarized_snapshot(
    req: SnapshotCreateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await compare_bom(
        left_type=req.left_type, left_id=req.left_id,
        right_type=req.right_type, right_id=req.right_id,
        max_levels=req.max_levels, effective_at=req.effective_at,
        include_child_fields=req.include_child_fields,
        include_relationship_props=req.include_relationship_props or None,
        line_key=req.line_key, compare_mode="summarized",
        include_substitutes=req.include_substitutes,
        include_effectivity=req.include_effectivity,
        user=user, db=db,
    )
    payload = _compare_result_to_summarized_rows(result)
    snapshot_id = f"bom-compare-summarized-snapshot-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "snapshot_id": snapshot_id,
        "created_at": now,
        "created_by": user.id,
        "name": req.name,
        "note": req.note,
        "compare": {
            "left_type": req.left_type,
            "left_id": req.left_id,
            "right_type": req.right_type,
            "right_id": req.right_id,
            "max_levels": req.max_levels,
            "effective_at": req.effective_at.isoformat() if req.effective_at else None,
            "include_child_fields": req.include_child_fields,
            "include_relationship_props": req.include_relationship_props or [],
            "line_key": req.line_key,
            "compare_mode": "summarized",
            "include_substitutes": req.include_substitutes,
            "include_effectivity": req.include_effectivity,
        },
        "summary": payload["summary"],
        "rows": payload["rows"],
        "row_total": len(payload["rows"]),
    }
    with _BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        _BOM_COMPARE_SUMMARIZED_SNAPSHOTS.append(snapshot)
    return snapshot


@bom_compare_router.get(
    "/compare/summarized/snapshots/compare",
    summary="Compare two saved summarized snapshots",
)
async def compare_bom_summarized_snapshots(
    left_snapshot_id: str = Query(...),
    right_snapshot_id: str = Query(...),
):
    left = _find_snapshot(left_snapshot_id)
    right = _find_snapshot(right_snapshot_id)
    diff = _diff_snapshot_rows(left["rows"], right["rows"])
    return {"source": "snapshot_vs_snapshot", **diff}


@bom_compare_router.get(
    "/compare/summarized/snapshots/compare/export",
    summary="Export snapshot vs snapshot diff",
)
async def compare_bom_summarized_snapshots_export(
    left_snapshot_id: str = Query(...),
    right_snapshot_id: str = Query(...),
    export_format: str = Query("csv"),
):
    _validate_export_format(export_format)
    left = _find_snapshot(left_snapshot_id)
    right = _find_snapshot(right_snapshot_id)
    diff = _diff_snapshot_rows(left["rows"], right["rows"])
    diff_result = {"source": "snapshot_vs_snapshot", **diff}
    return _export_diff(diff_result, export_format, "bom-compare-summarized-snapshot-diff")


@bom_compare_router.get(
    "/compare/summarized/snapshots/{snapshot_id}/compare/current",
    summary="Compare a saved snapshot with current live BOM state",
)
async def compare_bom_summarized_snapshot_with_current(
    snapshot_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    snap = _find_snapshot(snapshot_id)
    cmp = snap["compare"]
    result = await compare_bom(
        left_type=cmp["left_type"], left_id=cmp["left_id"],
        right_type=cmp["right_type"], right_id=cmp["right_id"],
        max_levels=cmp.get("max_levels", 10),
        effective_at=None,
        include_child_fields=cmp.get("include_child_fields", False),
        include_relationship_props=cmp.get("include_relationship_props") or None,
        line_key=cmp.get("line_key", "child_config"),
        compare_mode="summarized",
        include_substitutes=cmp.get("include_substitutes", False),
        include_effectivity=cmp.get("include_effectivity", False),
        user=user, db=db,
    )
    current_rows = _compare_result_to_summarized_rows(result)["rows"]
    diff = _diff_snapshot_rows(snap["rows"], current_rows)
    return {"source": "snapshot_vs_current", **diff}


@bom_compare_router.get(
    "/compare/summarized/snapshots/{snapshot_id}/compare/current/export",
    summary="Export snapshot vs current diff",
)
async def compare_bom_summarized_snapshot_with_current_export(
    snapshot_id: str,
    export_format: str = Query("csv"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_export_format(export_format)
    snap = _find_snapshot(snapshot_id)
    cmp = snap["compare"]
    result = await compare_bom(
        left_type=cmp["left_type"], left_id=cmp["left_id"],
        right_type=cmp["right_type"], right_id=cmp["right_id"],
        max_levels=cmp.get("max_levels", 10),
        effective_at=None,
        include_child_fields=cmp.get("include_child_fields", False),
        include_relationship_props=cmp.get("include_relationship_props") or None,
        line_key=cmp.get("line_key", "child_config"),
        compare_mode="summarized",
        include_substitutes=cmp.get("include_substitutes", False),
        include_effectivity=cmp.get("include_effectivity", False),
        user=user, db=db,
    )
    current_rows = _compare_result_to_summarized_rows(result)["rows"]
    diff = _diff_snapshot_rows(snap["rows"], current_rows)
    diff_result = {"source": "snapshot_vs_current", **diff}
    return _export_diff(diff_result, export_format, "bom-compare-summarized-snapshot-diff")


@bom_compare_router.get(
    "/compare/summarized/snapshots/{snapshot_id}/export",
    summary="Export a saved snapshot as CSV or Markdown",
)
async def export_bom_summarized_snapshot(
    snapshot_id: str,
    export_format: str = Query("csv"),
):
    _validate_export_format(export_format)
    snap = _find_snapshot(snapshot_id)
    rows = snap["rows"]

    if export_format == "json":
        return JSONResponse(content=snap)
    if export_format == "csv":
        return StreamingResponse(
            io.BytesIO(_rows_to_csv(rows).encode()),
            media_type="text/csv",
            headers={
                "content-disposition": f'attachment; filename="bom-compare-summarized-snapshot-{snapshot_id}.csv"'
            },
        )
    md = _rows_to_markdown(rows, f"BOM Compare Summarized Snapshot {snapshot_id}")
    return StreamingResponse(
        io.BytesIO(md.encode()),
        media_type="text/markdown",
        headers={
            "content-disposition": f'attachment; filename="bom-compare-summarized-snapshot-{snapshot_id}.md"'
        },
    )


@bom_compare_router.get(
    "/compare/summarized/snapshots/{snapshot_id}",
    summary="Get a saved snapshot detail",
)
async def get_bom_summarized_snapshot(snapshot_id: str):
    return _find_snapshot(snapshot_id)


@bom_compare_router.get(
    "/compare/summarized/snapshots",
    summary="List saved summarized snapshots",
)
async def list_bom_summarized_snapshots(
    created_by: Optional[int] = Query(None),
    name_contains: Optional[str] = Query(None),
    limit: int = Query(20),
    offset: int = Query(0),
):
    with _BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        filtered = list(_BOM_COMPARE_SUMMARIZED_SNAPSHOTS)

    if created_by is not None:
        filtered = [s for s in filtered if s.get("created_by") == created_by]
    if name_contains:
        lc = name_contains.lower()
        filtered = [s for s in filtered if lc in (s.get("name") or "").lower()]

    total = len(filtered)
    page = filtered[offset: offset + limit]

    snapshots = []
    for s in page:
        snapshots.append({
            "snapshot_id": s["snapshot_id"],
            "created_at": s.get("created_at"),
            "created_by": s.get("created_by"),
            "name": s.get("name"),
            "note": s.get("note"),
            "row_count": len(s.get("rows", [])),
            "rows": None,
        })

    return {
        "total": total,
        "count": len(snapshots),
        "limit": limit,
        "offset": offset,
        "snapshots": snapshots,
    }
