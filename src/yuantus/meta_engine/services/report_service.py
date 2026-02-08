"""
Report Service
Generates comparison and analysis reports.
Phase 5: Reporting
"""

from typing import Dict, Any, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.eco import ECO, ECOStage
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.manufacturing.models import ManufacturingBOM, Operation, Routing, WorkCenter
from yuantus.meta_engine.version.models import ItemVersion


class ReportService:
    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

    def get_summary(self) -> Dict[str, Any]:
        def _group_counts(rows, key_name: str) -> List[Dict[str, Any]]:
            return [{key_name: key, "count": count} for key, count in rows]

        items_total = self.session.query(func.count(Item.id)).scalar() or 0
        items_by_type = (
            self.session.query(Item.item_type_id, func.count(Item.id))
            .group_by(Item.item_type_id)
            .order_by(Item.item_type_id.asc())
            .all()
        )
        items_by_state = (
            self.session.query(Item.state, func.count(Item.id))
            .group_by(Item.state)
            .order_by(Item.state.asc())
            .all()
        )

        versions_total = self.session.query(func.count(ItemVersion.id)).scalar() or 0
        versions_by_state = (
            self.session.query(ItemVersion.state, func.count(ItemVersion.id))
            .group_by(ItemVersion.state)
            .order_by(ItemVersion.state.asc())
            .all()
        )

        files_total = self.session.query(func.count(FileContainer.id)).scalar() or 0
        files_by_doc_type = (
            self.session.query(FileContainer.document_type, func.count(FileContainer.id))
            .group_by(FileContainer.document_type)
            .order_by(FileContainer.document_type.asc())
            .all()
        )
        files_by_conversion_status = (
            self.session.query(FileContainer.conversion_status, func.count(FileContainer.id))
            .group_by(FileContainer.conversion_status)
            .order_by(FileContainer.conversion_status.asc())
            .all()
        )
        files_by_native = (
            self.session.query(FileContainer.is_native_cad, func.count(FileContainer.id))
            .group_by(FileContainer.is_native_cad)
            .order_by(FileContainer.is_native_cad.asc())
            .all()
        )
        files_by_connector = (
            self.session.query(FileContainer.cad_connector_id, func.count(FileContainer.id))
            .group_by(FileContainer.cad_connector_id)
            .order_by(FileContainer.cad_connector_id.asc())
            .all()
        )

        eco_total = self.session.query(func.count(ECO.id)).scalar() or 0
        eco_by_state = (
            self.session.query(ECO.state, func.count(ECO.id))
            .group_by(ECO.state)
            .order_by(ECO.state.asc())
            .all()
        )
        eco_by_stage_rows = (
            self.session.query(ECO.stage_id, ECOStage.name, func.count(ECO.id))
            .outerjoin(ECOStage, ECOStage.id == ECO.stage_id)
            .group_by(ECO.stage_id, ECOStage.name)
            .order_by(ECOStage.name.asc())
            .all()
        )
        eco_by_stage = [
            {"stage_id": stage_id, "stage_name": stage_name, "count": count}
            for stage_id, stage_name, count in eco_by_stage_rows
        ]

        jobs_total = self.session.query(func.count(ConversionJob.id)).scalar() or 0
        jobs_by_status = (
            self.session.query(ConversionJob.status, func.count(ConversionJob.id))
            .group_by(ConversionJob.status)
            .order_by(ConversionJob.status.asc())
            .all()
        )
        jobs_by_task = (
            self.session.query(ConversionJob.task_type, func.count(ConversionJob.id))
            .group_by(ConversionJob.task_type)
            .order_by(ConversionJob.task_type.asc())
            .all()
        )

        mboms_total = self.session.query(func.count(ManufacturingBOM.id)).scalar() or 0
        mboms_by_state = (
            self.session.query(ManufacturingBOM.state, func.count(ManufacturingBOM.id))
            .group_by(ManufacturingBOM.state)
            .order_by(ManufacturingBOM.state.asc())
            .all()
        )
        mboms_by_plant = (
            self.session.query(ManufacturingBOM.plant_code, func.count(ManufacturingBOM.id))
            .group_by(ManufacturingBOM.plant_code)
            .order_by(ManufacturingBOM.plant_code.asc())
            .all()
        )
        mboms_by_line = (
            self.session.query(ManufacturingBOM.line_code, func.count(ManufacturingBOM.id))
            .group_by(ManufacturingBOM.line_code)
            .order_by(ManufacturingBOM.line_code.asc())
            .all()
        )
        mboms_by_type = (
            self.session.query(ManufacturingBOM.bom_type, func.count(ManufacturingBOM.id))
            .group_by(ManufacturingBOM.bom_type)
            .order_by(ManufacturingBOM.bom_type.asc())
            .all()
        )

        routings_total = self.session.query(func.count(Routing.id)).scalar() or 0
        routings_by_state = (
            self.session.query(Routing.state, func.count(Routing.id))
            .group_by(Routing.state)
            .order_by(Routing.state.asc())
            .all()
        )
        routings_by_plant = (
            self.session.query(Routing.plant_code, func.count(Routing.id))
            .group_by(Routing.plant_code)
            .order_by(Routing.plant_code.asc())
            .all()
        )
        routings_by_line = (
            self.session.query(Routing.line_code, func.count(Routing.id))
            .group_by(Routing.line_code)
            .order_by(Routing.line_code.asc())
            .all()
        )

        workcenters_total = self.session.query(func.count(WorkCenter.id)).scalar() or 0
        workcenters_by_active = (
            self.session.query(WorkCenter.is_active, func.count(WorkCenter.id))
            .group_by(WorkCenter.is_active)
            .order_by(WorkCenter.is_active.asc())
            .all()
        )
        workcenters_by_plant = (
            self.session.query(WorkCenter.plant_code, func.count(WorkCenter.id))
            .group_by(WorkCenter.plant_code)
            .order_by(WorkCenter.plant_code.asc())
            .all()
        )

        operations_total = self.session.query(func.count(Operation.id)).scalar() or 0
        operations_by_type = (
            self.session.query(Operation.operation_type, func.count(Operation.id))
            .group_by(Operation.operation_type)
            .order_by(Operation.operation_type.asc())
            .all()
        )

        return {
            "items": {
                "total": items_total,
                "by_type": _group_counts(items_by_type, "item_type_id"),
                "by_state": _group_counts(items_by_state, "state"),
            },
            "versions": {
                "total": versions_total,
                "by_state": _group_counts(versions_by_state, "state"),
            },
            "files": {
                "total": files_total,
                "by_document_type": _group_counts(files_by_doc_type, "document_type"),
                "by_conversion_status": _group_counts(files_by_conversion_status, "conversion_status"),
                "by_is_native_cad": _group_counts(files_by_native, "is_native_cad"),
                "by_cad_connector_id": _group_counts(files_by_connector, "cad_connector_id"),
            },
            "ecos": {
                "total": eco_total,
                "by_state": _group_counts(eco_by_state, "state"),
                "by_stage": eco_by_stage,
            },
            "jobs": {
                "total": jobs_total,
                "by_status": _group_counts(jobs_by_status, "status"),
                "by_task_type": _group_counts(jobs_by_task, "task_type"),
            },
            "manufacturing": {
                "mboms": {
                    "total": mboms_total,
                    "by_state": _group_counts(mboms_by_state, "state"),
                    "by_plant_code": _group_counts(mboms_by_plant, "plant_code"),
                    "by_line_code": _group_counts(mboms_by_line, "line_code"),
                    "by_bom_type": _group_counts(mboms_by_type, "bom_type"),
                },
                "routings": {
                    "total": routings_total,
                    "by_state": _group_counts(routings_by_state, "state"),
                    "by_plant_code": _group_counts(routings_by_plant, "plant_code"),
                    "by_line_code": _group_counts(routings_by_line, "line_code"),
                },
                "workcenters": {
                    "total": workcenters_total,
                    "by_is_active": _group_counts(workcenters_by_active, "is_active"),
                    "by_plant_code": _group_counts(workcenters_by_plant, "plant_code"),
                },
                "operations": {
                    "total": operations_total,
                    "by_operation_type": _group_counts(operations_by_type, "operation_type"),
                },
            },
        }

    def generate_bom_comparison(self, item_id_a: str, item_id_b: str) -> Dict[str, Any]:
        """
        Compares two BOM structures (Quantity Rollup / Summary).
        Can compare two different items, or two versions of the same item.
        """
        bom_a = self.bom_service.get_bom_structure(
            item_id_a, levels=-1
        )  # Full explosion
        bom_b = self.bom_service.get_bom_structure(item_id_b, levels=-1)

        flat_a = self._flatten_bom(bom_a)
        flat_b = self._flatten_bom(bom_b)

        # Compare
        all_keys = set(flat_a.keys()) | set(flat_b.keys())
        diffs = []
        stats = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

        for key in all_keys:
            val_a = flat_a.get(key)
            val_b = flat_b.get(key)

            item_info = val_a or val_b  # Get name info from whichever exists
            name = item_info.get("name", "Unknown")

            if not val_a:
                diffs.append(
                    {
                        "id": key,
                        "name": name,
                        "status": "added",
                        "new_qty": val_b["qty"],
                    }
                )
                stats["added"] += 1
            elif not val_b:
                diffs.append(
                    {
                        "id": key,
                        "name": name,
                        "status": "removed",
                        "old_qty": val_a["qty"],
                    }
                )
                stats["removed"] += 1
            else:
                if abs(val_a["qty"] - val_b["qty"]) > 0.000001:
                    diffs.append(
                        {
                            "id": key,
                            "name": name,
                            "status": "modified",
                            "old_qty": val_a["qty"],
                            "new_qty": val_b["qty"],
                            "delta": val_b["qty"] - val_a["qty"],
                        }
                    )
                    stats["modified"] += 1
                else:
                    stats["unchanged"] += 1

        return {
            "item_a": bom_a.get("id"),
            "item_b": bom_b.get("id"),
            "stats": stats,
            "differences": diffs,
        }

    def _flatten_bom(self, bom_tree: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Flattens a BOM tree into a summary of {child_id: {qty: total_qty, name: ...}}
        """
        summary = {}

        def _recurse(node, multiplier=1.0):
            if "children" in node:
                for child_entry in node["children"]:
                    child_data = child_entry["child"]
                    child_id = child_data["id"]

                    # Get properties for quantity
                    rel = child_entry["relationship"]
                    props = rel.get("properties", {})
                    try:
                        qty = float(props.get("quantity", props.get("qty", 1.0)))
                    except (ValueError, TypeError):
                        qty = 1.0

                    total_qty = qty * multiplier

                    # Get Name for display
                    child_props = child_data.get("properties", {})
                    name = child_props.get("name", "Unknown")

                    if child_id not in summary:
                        summary[child_id] = {"qty": 0.0, "name": name}
                    summary[child_id]["qty"] += total_qty

                    # Recurse
                    _recurse(child_data, total_qty)

        _recurse(bom_tree)
        return summary

    def get_flattened_bom(self, item_id: str) -> List[Dict[str, Any]]:
        """
        Returns a list of all components with total quantities (Rollup).
        """
        tree = self.bom_service.get_bom_structure(item_id, levels=-1)
        summary = self._flatten_bom(tree)

        result = []
        for cid, data in summary.items():
            result.append(
                {"id": cid, "name": data["name"], "total_quantity": data["qty"]}
            )
        return result
