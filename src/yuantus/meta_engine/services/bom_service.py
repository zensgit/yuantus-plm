from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from yuantus.meta_engine.models.item import Item
from .effectivity_service import EffectivityService


class BOMService:
    """
    Manages Product Structure (BOM).
    Handles Explosion, Where-Used, and Circularity Checks.
    """

    def __init__(self, session: Session):
        self.session = session
        self.eff_service = EffectivityService(session)

    def get_bom_structure(
        self,
        item_id: str,
        levels: int = 10,
        effective_date: datetime = None,
        include_substitutes: bool = False,
    ) -> Dict[str, Any]:
        """
        Return hierarchical BOM structure.
        Supports Effectivity filtering.
        """
        root = self.session.get(Item, item_id)
        if not root:
            raise ValueError(f"Item {item_id} not found")

        return self._build_tree(
            root,
            current_level=0,
            max_level=levels,
            effective_date=effective_date,
            include_substitutes=include_substitutes,
        )

    def _build_tree(
        self,
        parent_item: Item,
        current_level: int,
        max_level: int,
        effective_date: datetime = None,
        include_substitutes: bool = False,
    ) -> Dict[str, Any]:
        node = parent_item.to_dict()
        node["children"] = []

        if max_level != -1 and current_level >= max_level:
            return node

        # Find relationships where source_id = parent_item.id
        rels = (
            self.session.query(Item)
            .filter(
                Item.source_id == parent_item.id,
                Item.is_current.is_(True),
            )
            .all()
        )

        # print(f"DEBUG: Processing {parent_item.id}, found {len(rels)} relationships")

        for rel in rels:
            if not rel.related_id:
                continue

            # Check Effectivity (on the Relationship Item)
            if effective_date:
                # If relationship is not effective at this date, skip
                if not self.eff_service.check_date_effectivity(rel.id, effective_date):
                    continue

            child_item = self.session.get(Item, rel.related_id)
            if not child_item or not child_item.is_current:
                continue

            rel_dict = rel.to_dict()
            # Explicitly include properties for downstream processing (e.g. ECOService)
            rel_dict["properties"] = rel.properties or {}

            child_node = {
                "relationship": rel_dict,
                "child": self._build_tree(
                    child_item,
                    current_level + 1,
                    max_level,
                    effective_date,
                    include_substitutes=include_substitutes,
                ),
            }

            # Fetch BOM-specific substitutes
            if include_substitutes:
                from .substitute_service import SubstituteService

                sub_svc = SubstituteService(self.session)
                child_node["substitutes"] = sub_svc.get_bom_substitutes(rel.id)

            node["children"].append(child_node)

        return node

    def detect_cycle(self, parent_id: str, child_id: str) -> bool:
        """
        Check if adding parent -> child creates a cycle.
        Algorithm: BFS/DFS starting from 'child'. If 'parent' is found, it's a cycle.
        """
        result = self.detect_cycle_with_path(parent_id, child_id)
        return result["has_cycle"]

    def detect_cycle_with_path(self, parent_id: str, child_id: str) -> Dict[str, Any]:
        """
        Check if adding parent -> child creates a cycle.
        Returns the cycle path if found.

        Algorithm: BFS starting from 'child'. If 'parent' is found, reconstruct path.

        Returns:
            {
                "has_cycle": bool,
                "cycle_path": List[str] | None  # e.g. ["A", "B", "C", "A"] for A->B->C->A
            }
        """
        if parent_id == child_id:
            return {
                "has_cycle": True,
                "cycle_path": [parent_id, child_id]
            }

        # BFS with path tracking
        # queue items: (current_id, path_to_current)
        queue: List[tuple] = [(child_id, [parent_id, child_id])]
        visited = set()

        while queue:
            curr, path = queue.pop(0)

            if curr == parent_id:
                # Found cycle! path already includes parent_id at start
                return {
                    "has_cycle": True,
                    "cycle_path": path
                }

            if curr in visited:
                continue
            visited.add(curr)

            # Get all children of curr
            rels = (
                self.session.query(Item)
                .filter(Item.source_id == curr, Item.is_current.is_(True))
                .all()
            )

            for r in rels:
                if r.related_id and r.related_id not in visited:
                    queue.append((r.related_id, path + [r.related_id]))

        return {
            "has_cycle": False,
            "cycle_path": None
        }

    def get_where_used(
        self,
        item_id: str,
        recursive: bool = False,
        max_levels: int = 10,
        _current_level: int = 0,
        _visited: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find all parents that use this item.
        If recursive=True, finds parents of parents up to max_levels.
        """
        if _visited is None:
            _visited = set()

        if item_id in _visited:
            return []
        _visited.add(item_id)

        if _current_level >= max_levels:
            return []

        rels = (
            self.session.query(Item)
            .filter(Item.related_id == item_id, Item.is_current.is_(True))
            .all()
        )

        parents = []
        for rel in rels:
            if not rel.source_id:
                continue
            parent = self.session.get(Item, rel.source_id)
            if parent:
                parent_entry = {
                    "relationship": rel.to_dict(),
                    "parent": parent.to_dict(),
                    "level": _current_level + 1,
                }
                parents.append(parent_entry)

                if recursive:
                    grandparents = self.get_where_used(
                        parent.id,
                        recursive=True,
                        max_levels=max_levels,
                        _current_level=_current_level + 1,
                        _visited=_visited,
                    )
                    parents.extend(grandparents)

        return parents

    def get_bom_for_version(self, version_id: str, levels: int = 10) -> Dict[str, Any]:
        """
        Get BOM structure as defined by the context of a specific ItemVersion.
        Uses the version's effectivity date or creation date to resolve structure.
        """
        from yuantus.meta_engine.version.models import ItemVersion
        from yuantus.meta_engine.models.effectivity import Effectivity

        ver = self.session.get(ItemVersion, version_id)
        if not ver:
            raise ValueError(f"Version {version_id} not found")

        # Determine effective context date
        # 1. Check if there's an explicit Date Effectivity
        eff = (
            self.session.query(Effectivity)
            .filter(Effectivity.version_id == version_id)
            .filter(Effectivity.effectivity_type == "Date")
            .first()
        )

        target_date = eff.start_date if eff else ver.created_at

        # If no created_at (e.g. legacy), default to now
        if not target_date:
            target_date = datetime.utcnow()

        return self.get_bom_structure(ver.item_id, levels, effective_date=target_date)

    def get_bom_line_by_parent_child(
        self, parent_item_id: str, child_item_id: str
    ) -> Optional[Item]:
        """
        Get the BOM line (relationship item) between a parent and a child.
        """
        return (
            self.session.query(Item)
            .filter(
                Item.source_id == parent_item_id,
                Item.related_id == child_item_id,
                Item.is_current.is_(True),
            )
            .first()
        )

    def merge_bom(
        self, target_item_id: str, source_version_id: str, user_id: int
    ) -> Dict[str, Any]:
        """
        Merges BOM lines from a source version into the current target item.
        Adds missing lines. Updates existing lines (simple overwrite).
        """
        # 1. Get Source BOM (Level 1)
        # We need the effective date of the source version
        from yuantus.meta_engine.version.models import ItemVersion

        source_ver = self.session.get(ItemVersion, source_version_id)
        if not source_ver:
            raise ValueError("Source version not found")

        # Use get_bom_for_version but restriction to level 1 to get direct children
        source_structure = self.get_bom_for_version(source_version_id, levels=1)
        source_children = source_structure.get("children", [])

        # 2. Get Target BOM (Current)
        # We query DB directly to get Relationship Items
        current_rels = (
            self.session.query(Item)
            .filter(Item.source_id == target_item_id, Item.is_current.is_(True))
            .all()
        )
        current_map = {rel.related_id: rel for rel in current_rels if rel.related_id}

        stats = {"added": 0, "updated": 0}

        # 3. Merge
        import uuid

        # But we create Item directly here for speed/access

        system_keys = {
            "id",
            "item_type_id",
            "config_id",
            "generation",
            "is_current",
            "state",
            "current_state",
            "current_version_id",
            "created_by_id",
            "created_on",
            "modified_by_id",
            "modified_on",
            "owner_id",
            "permission_id",
            "source_id",
            "related_id",
            "children",
            "properties",
            "substitutes",
        }

        for child_node in source_children:
            rel_data = child_node["relationship"]
            child_data = child_node["child"]
            child_id = child_data["id"]

            # Properties to merge (filter out system keys)
            props = {k: v for k, v in rel_data.items() if k not in system_keys}

            if child_id in current_map:
                # Update existing
                rel_item = current_map[child_id]
                # Simple merge: overwrite properties
                current_props = dict(rel_item.properties or {})
                current_props.update(props)
                rel_item.properties = current_props
                rel_item.modified_by_id = user_id
                stats["updated"] += 1
            else:
                # Add new relationship
                # We need to know the ItemType. Assuming "Part BOM" or same as source.
                rel_type_id = rel_data.get("type", "Part BOM")

                new_rel = Item(
                    id=str(uuid.uuid4()),
                    item_type_id=rel_type_id,
                    config_id=str(uuid.uuid4()),
                    generation=1,
                    is_current=True,
                    state="Active",
                    properties=props,
                    source_id=target_item_id,
                    related_id=child_id,
                    created_by_id=user_id,
                )
                self.session.add(new_rel)
                stats["added"] += 1

        self.session.flush()
        return stats

    def add_child(
        self,
        parent_id: str,
        child_id: str,
        user_id: Optional[int] = None,
        quantity: float = 1.0,
        uom: str = "EA",
        find_num: Optional[str] = None,
        refdes: Optional[str] = None,
        effectivity_from: Optional[datetime] = None,
        effectivity_to: Optional[datetime] = None,
        extra_properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add a child item to a parent BOM.

        Args:
            parent_id: Parent item ID
            child_id: Child item ID to add
            user_id: User performing the action
            quantity: Quantity (default 1.0)
            uom: Unit of measure (default "EA")
            find_num: Find number / reference designator number
            refdes: Reference designators (comma-separated for multiple)
            effectivity_from: Start date for effectivity
            effectivity_to: End date for effectivity
            extra_properties: Additional properties for the BOM line

        Returns:
            {
                "ok": True,
                "relationship_id": str,
                "parent_id": str,
                "child_id": str
            }

        Raises:
            ValueError: If parent/child not found or cycle detected
        """
        import uuid

        # Validate parent exists
        parent = self.session.get(Item, parent_id)
        if not parent:
            raise ValueError(f"Parent item {parent_id} not found")

        # Validate child exists
        child = self.session.get(Item, child_id)
        if not child:
            raise ValueError(f"Child item {child_id} not found")

        # Check for cycle
        cycle_result = self.detect_cycle_with_path(parent_id, child_id)
        if cycle_result["has_cycle"]:
            raise CycleDetectedError(
                parent_id=parent_id,
                child_id=child_id,
                cycle_path=cycle_result["cycle_path"]
            )

        # Check if relationship already exists
        existing = self.get_bom_line_by_parent_child(parent_id, child_id)
        if existing:
            raise ValueError(f"BOM relationship already exists: {parent_id} -> {child_id}")

        # Build properties
        properties = {
            "quantity": quantity,
            "uom": uom,
        }
        if find_num:
            properties["find_num"] = find_num
        if refdes:
            properties["refdes"] = refdes
        if effectivity_from:
            properties["effectivity_from"] = effectivity_from.isoformat()
        if effectivity_to:
            properties["effectivity_to"] = effectivity_to.isoformat()
        if extra_properties:
            properties.update(extra_properties)

        # Create relationship Item
        rel_id = str(uuid.uuid4())
        rel = Item(
            id=rel_id,
            item_type_id="Part BOM",
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            properties=properties,
            source_id=parent_id,
            related_id=child_id,
            created_by_id=user_id,
            permission_id=parent.permission_id,
        )
        self.session.add(rel)
        self.session.flush()

        # Create Effectivity record if dates are provided (S3.2)
        # This enables /bom/{id}/effective filtering via meta_effectivities table
        effectivity_id = None
        if effectivity_from is not None or effectivity_to is not None:
            eff = self.eff_service.create_effectivity(
                item_id=rel_id,  # BOM relationship item ID
                effectivity_type="Date",
                start_date=effectivity_from,
                end_date=effectivity_to,
                created_by_id=user_id,
            )
            effectivity_id = eff.id

        return {
            "ok": True,
            "relationship_id": rel_id,
            "parent_id": parent_id,
            "child_id": child_id,
            "effectivity_id": effectivity_id,
        }

    def remove_child(
        self,
        parent_id: str,
        child_id: str,
    ) -> Dict[str, Any]:
        """
        Remove a child from a parent BOM.

        Args:
            parent_id: Parent item ID
            child_id: Child item ID to remove

        Returns:
            {"ok": True, "relationship_id": str}

        Raises:
            ValueError: If relationship not found
        """
        rel = self.get_bom_line_by_parent_child(parent_id, child_id)
        if not rel:
            raise ValueError(f"BOM relationship not found: {parent_id} -> {child_id}")

        rel_id = rel.id
        self.session.delete(rel)
        self.session.flush()

        return {
            "ok": True,
            "relationship_id": rel_id,
        }

    def get_tree(
        self,
        item_id: str,
        depth: int = 10,
        effective_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get BOM tree structure with specified depth.

        This is similar to get_bom_structure but uses explicit depth parameter
        and includes item names for easier consumption.

        Args:
            item_id: Root item ID
            depth: Maximum depth to traverse (-1 for unlimited)
            effective_date: Optional date for effectivity filtering

        Returns:
            Tree structure with children
        """
        return self.get_bom_structure(
            item_id,
            levels=depth,
            effective_date=effective_date,
        )

    def compare_bom_trees(
        self,
        left_tree: Dict[str, Any],
        right_tree: Dict[str, Any],
        include_relationship_props: Optional[List[str]] = None,
        include_child_fields: bool = False,
    ) -> Dict[str, Any]:
        """
        Compare two BOM trees and return added/removed/changed edges.
        """
        left_edges = self._flatten_tree(
            left_tree,
            include_relationship_props=include_relationship_props,
            include_child_fields=include_child_fields,
        )
        right_edges = self._flatten_tree(
            right_tree,
            include_relationship_props=include_relationship_props,
            include_child_fields=include_child_fields,
        )

        left_keys = set(left_edges.keys())
        right_keys = set(right_edges.keys())

        added_keys = sorted(right_keys - left_keys)
        removed_keys = sorted(left_keys - right_keys)

        changed_keys = []
        for key in sorted(left_keys & right_keys):
            left_entry = left_edges[key]
            right_entry = right_edges[key]
            if self._properties_changed(left_entry, right_entry):
                changed_keys.append(key)

        added = [self._format_entry(right_edges[k]) for k in added_keys]
        removed = [self._format_entry(left_edges[k]) for k in removed_keys]
        changed = [
            self._format_changed_entry(left_edges[k], right_edges[k])
            for k in changed_keys
        ]

        return {
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "changed": len(changed),
            },
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    def _flatten_tree(
        self,
        tree: Dict[str, Any],
        include_relationship_props: Optional[List[str]] = None,
        include_child_fields: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        edges: Dict[str, Dict[str, Any]] = {}

        def walk(node: Dict[str, Any]) -> None:
            parent_id = node.get("id")
            parent_config_id = node.get("config_id") or parent_id
            children = node.get("children") or []
            for child_entry in children:
                rel = child_entry.get("relationship") or {}
                child = child_entry.get("child") or {}
                child_id = child.get("id")
                child_config_id = child.get("config_id") or child_id

                raw_props = self._select_relationship_properties(
                    rel,
                    include_relationship_props=include_relationship_props,
                )
                norm_props = self._normalize_properties(raw_props)

                key = f"{parent_config_id}::{child_config_id}"
                entry: Dict[str, Any] = {
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "parent_config_id": parent_config_id,
                    "child_config_id": child_config_id,
                    "properties": raw_props,
                    "normalized_properties": norm_props,
                }

                if include_child_fields:
                    entry["parent"] = {
                        "id": parent_id,
                        "config_id": parent_config_id,
                        "item_number": node.get("item_number"),
                        "name": node.get("name"),
                    }
                    entry["child"] = {
                        "id": child_id,
                        "config_id": child_config_id,
                        "item_number": child.get("item_number"),
                        "name": child.get("name"),
                    }

                edges[key] = entry
                walk(child)

        walk(tree)
        return edges

    def _select_relationship_properties(
        self,
        relationship: Dict[str, Any],
        include_relationship_props: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        props = relationship.get("properties") or {}
        if include_relationship_props:
            return {k: props.get(k) for k in include_relationship_props if k in props}

        default_keys = [
            "quantity",
            "uom",
            "find_num",
            "refdes",
            "effectivity_from",
            "effectivity_to",
        ]
        selected = {k: props.get(k) for k in default_keys if k in props}
        return selected if selected else props.copy()

    def _normalize_properties(self, props: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in props.items():
            normalized[key] = self._normalize_value(key, value)
        return normalized

    def _normalize_value(self, key: str, value: Any) -> Any:
        if value is None:
            return None
        if key == "quantity":
            try:
                return float(Decimal(str(value)))
            except (InvalidOperation, ValueError):
                return value
        if key == "uom":
            return str(value).strip().upper()
        if key == "find_num":
            return str(value).strip()
        if key == "refdes":
            return tuple(self._normalize_refdes(value))
        if key in {"effectivity_from", "effectivity_to"}:
            return self._normalize_datetime(value)
        return value

    def _normalize_refdes(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            parts = value
        else:
            parts = re.split(r"[;,|\s]+", str(value))
        cleaned = [p.strip().upper() for p in parts if str(p).strip()]
        return sorted(set(cleaned))

    def _normalize_datetime(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).isoformat()
            except ValueError:
                return value.strip()
        return value

    def _properties_changed(
        self,
        left_entry: Dict[str, Any],
        right_entry: Dict[str, Any],
        tolerance: float = 1e-6,
    ) -> bool:
        left_props = left_entry.get("normalized_properties") or {}
        right_props = right_entry.get("normalized_properties") or {}

        keys = set(left_props.keys()) | set(right_props.keys())
        for key in keys:
            left_val = left_props.get(key)
            right_val = right_props.get(key)
            if key == "quantity" and left_val is not None and right_val is not None:
                try:
                    if abs(float(left_val) - float(right_val)) <= tolerance:
                        continue
                except (TypeError, ValueError):
                    pass
            if left_val != right_val:
                return True
        return False

    def _format_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        result = {
            "parent_id": entry.get("parent_id"),
            "child_id": entry.get("child_id"),
            "properties": entry.get("properties", {}),
        }
        if "parent" in entry:
            result["parent"] = entry["parent"]
        if "child" in entry:
            result["child"] = entry["child"]
        return result

    def _format_changed_entry(
        self,
        left_entry: Dict[str, Any],
        right_entry: Dict[str, Any],
    ) -> Dict[str, Any]:
        left_props = left_entry.get("properties") or {}
        right_props = right_entry.get("properties") or {}
        left_norm = left_entry.get("normalized_properties") or {}
        right_norm = right_entry.get("normalized_properties") or {}

        diffs = {}
        for key in set(left_norm.keys()) | set(right_norm.keys()):
            if left_norm.get(key) != right_norm.get(key):
                diffs[key] = (left_props.get(key), right_props.get(key))

        before = {k: v[0] for k, v in diffs.items()}
        after = {k: v[1] for k, v in diffs.items()}

        result = {
            "parent_id": left_entry.get("parent_id"),
            "child_id": left_entry.get("child_id"),
            "before": before,
            "after": after,
        }
        if "parent" in left_entry:
            result["parent"] = left_entry["parent"]
        if "child" in left_entry:
            result["child"] = left_entry["child"]
        return result


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in BOM structure."""

    def __init__(self, parent_id: str, child_id: str, cycle_path: List[str]):
        self.parent_id = parent_id
        self.child_id = child_id
        self.cycle_path = cycle_path
        path_str = " -> ".join(cycle_path)
        super().__init__(f"Cycle detected: {path_str}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": "CYCLE_DETECTED",
            "message": str(self),
            "parent_id": self.parent_id,
            "child_id": self.child_id,
            "cycle_path": self.cycle_path,
        }
