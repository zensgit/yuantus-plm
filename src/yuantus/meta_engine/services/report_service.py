"""
Report Service
Generates comparison and analysis reports.
Phase 5: Reporting
"""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from yuantus.meta_engine.services.bom_service import BOMService


class ReportService:
    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)

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
