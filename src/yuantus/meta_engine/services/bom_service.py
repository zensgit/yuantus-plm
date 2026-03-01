from typing import List, Dict, Any, Optional
import json
import csv
import io
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from yuantus.meta_engine.models.item import Item
from .effectivity_service import EffectivityService, EffectivityContext


class BOMService:
    """
    Manages Product Structure (BOM).
    Handles Explosion, Where-Used, and Circularity Checks.
    """
    LINE_FIELD_KEYS = (
        "quantity",
        "uom",
        "find_num",
        "refdes",
        "effectivity_from",
        "effectivity_to",
        "effectivities",
        "substitutes",
        "config_condition",
    )
    MAJOR_FIELDS = {
        "quantity",
        "uom",
        "effectivity_from",
        "effectivity_to",
        "effectivities",
    }
    MINOR_FIELDS = {"find_num", "refdes", "substitutes", "config_condition"}
    FIELD_DESCRIPTIONS = {
        "quantity": "BOM quantity on the relationship line.",
        "uom": "Unit of measure for the BOM quantity.",
        "find_num": "BOM position/find number.",
        "refdes": "Reference designator(s) for BOM line.",
        "effectivity_from": "Effectivity start datetime (ISO).",
        "effectivity_to": "Effectivity end datetime (ISO).",
        "effectivities": "Expanded effectivity records attached to the line.",
        "substitutes": "Substitute items for the BOM line.",
        "config_condition": "Configuration condition (JSON) for variant BOM selection.",
    }
    FIELD_NORMALIZATION = {
        "quantity": "float",
        "uom": "upper-case string",
        "find_num": "trimmed string",
        "refdes": "sorted unique list",
        "effectivity_from": "ISO datetime string",
        "effectivity_to": "ISO datetime string",
        "effectivities": "sorted tuples (type,start,end,payload)",
        "substitutes": "sorted tuples (item_id,rank,note)",
        "config_condition": "json expression",
    }
    COMPARE_MODES = {
        "only_product": {
            "line_key": "child_config",
            "include_relationship_props": [],
            "aggregate_quantities": False,
            "aliases": ["only"],
            "description": "Compare by parent/child config only.",
        },
        "summarized": {
            "line_key": "child_config",
            "include_relationship_props": ["quantity", "uom"],
            "aggregate_quantities": True,
            "aliases": ["summary"],
            "description": "Aggregate quantities for identical children.",
        },
        "num_qty": {
            "line_key": "child_config_find_num_qty",
            "include_relationship_props": ["quantity", "uom", "find_num"],
            "aggregate_quantities": False,
            "aliases": ["numqty"],
            "description": "Compare by child config + find_num + quantity.",
        },
        "by_position": {
            "line_key": "child_config_find_num",
            "include_relationship_props": ["quantity", "uom", "find_num"],
            "aggregate_quantities": False,
            "aliases": ["by_pos", "position"],
            "description": "Compare by child config + find_num.",
        },
        "by_reference": {
            "line_key": "child_config_refdes",
            "include_relationship_props": ["quantity", "uom", "refdes"],
            "aggregate_quantities": False,
            "aliases": ["by_ref", "reference"],
            "description": "Compare by child config + refdes.",
        },
    }
    LINE_KEY_OPTIONS = (
        "child_config",
        "child_id",
        "relationship_id",
        "child_config_find_num",
        "child_config_refdes",
        "child_config_find_refdes",
        "child_id_find_num",
        "child_id_refdes",
        "child_id_find_refdes",
        "child_config_find_num_qty",
        "child_id_find_num_qty",
        "line_full",
    )
    COMPARE_DEFAULTS = {
        "max_levels": 10,
        "line_key": "child_config",
        "include_substitutes": False,
        "include_effectivity": False,
    }
    DELTA_EXPORT_FIELDS = (
        "op",
        "line_key",
        "parent_id",
        "child_id",
        "relationship_id",
        "severity",
        "risk_level",
        "change_count",
        "field",
        "before",
        "after",
        "properties",
    )

    def __init__(self, session: Session):
        self.session = session
        self.eff_service = EffectivityService(session)

    @staticmethod
    def resolve_compare_mode(
        mode: Optional[str],
    ) -> tuple[Optional[str], Optional[List[str]], bool]:
        if not mode:
            return None, None, False
        normalized = mode.strip().lower().replace("-", "_")
        for mode_key, spec in BOMService.COMPARE_MODES.items():
            aliases = spec.get("aliases") or []
            if normalized == mode_key or normalized in aliases:
                return (
                    spec.get("line_key"),
                    spec.get("include_relationship_props"),
                    bool(spec.get("aggregate_quantities")),
                )
        raise ValueError(
            "compare_mode must be one of: only_product, summarized, num_qty, "
            "by_position, by_reference"
        )

    @classmethod
    def line_schema(cls) -> List[Dict[str, Any]]:
        fields = []
        for field in cls.LINE_FIELD_KEYS:
            fields.append(
                {
                    "field": field,
                    "severity": cls.field_severity(field),
                    "normalized": cls.FIELD_NORMALIZATION.get(field, "raw"),
                    "description": cls.FIELD_DESCRIPTIONS.get(field, ""),
                }
            )
        return fields

    @classmethod
    def compare_schema(cls) -> Dict[str, Any]:
        fields = cls.line_schema()

        modes = []
        for mode, spec in cls.COMPARE_MODES.items():
            modes.append(
                {
                    "mode": mode,
                    "line_key": spec.get("line_key"),
                    "include_relationship_props": spec.get("include_relationship_props", []),
                    "aggregate_quantities": bool(spec.get("aggregate_quantities")),
                    "aliases": spec.get("aliases", []),
                    "description": spec.get("description", ""),
                }
            )

        return {
            "line_fields": fields,
            "compare_modes": modes,
            "line_key_options": list(cls.LINE_KEY_OPTIONS),
            "defaults": dict(cls.COMPARE_DEFAULTS),
        }

    def get_bom_structure(
        self,
        item_id: str,
        levels: int = 10,
        effective_date: datetime = None,
        include_substitutes: bool = False,
        relationship_types: Optional[List[str]] = None,
        config_selection: Optional[Dict[str, Any]] = None,
        lot_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        unit_position: Optional[str] = None,
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
            relationship_types=relationship_types,
            config_selection=config_selection,
            lot_number=lot_number,
            serial_number=serial_number,
            unit_position=unit_position,
        )

    @staticmethod
    def _build_effectivity_context(
        effective_date: Optional[datetime],
        lot_number: Optional[str],
        serial_number: Optional[str],
        unit_position: Optional[str],
    ) -> Optional[EffectivityContext]:
        if (
            effective_date is None
            and lot_number is None
            and serial_number is None
            and unit_position is None
        ):
            return None
        return EffectivityContext(
            reference_date=effective_date,
            lot_number=lot_number,
            serial_number=serial_number,
            unit_position=unit_position,
        )

    def _build_tree(
        self,
        parent_item: Item,
        current_level: int,
        max_level: int,
        effective_date: datetime = None,
        include_substitutes: bool = False,
        relationship_types: Optional[List[str]] = None,
        config_selection: Optional[Dict[str, Any]] = None,
        lot_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        unit_position: Optional[str] = None,
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
        )

        if relationship_types:
            rels = rels.filter(Item.item_type_id.in_(relationship_types))

        rels = rels.all()

        # print(f"DEBUG: Processing {parent_item.id}, found {len(rels)} relationships")

        for rel in rels:
            if not rel.related_id:
                continue

            rel_props = rel.properties or {}
            if config_selection is not None:
                if not self._match_config_condition(
                    rel_props.get("config_condition"), config_selection
                ):
                    continue

            eff_ctx = self._build_effectivity_context(
                effective_date, lot_number, serial_number, unit_position
            )
            if eff_ctx:
                if not self.eff_service.check_effectivity(rel.id, eff_ctx):
                    continue

            child_item = self.session.get(Item, rel.related_id)
            if not child_item or not child_item.is_current:
                continue

            rel_dict = rel.to_dict()
            # Explicitly include properties for downstream processing (e.g. ECOService)
            rel_dict["properties"] = rel_props

            child_node = {
                "relationship": rel_dict,
                "child": self._build_tree(
                    child_item,
                    current_level + 1,
                    max_level,
                    effective_date,
                    include_substitutes=include_substitutes,
                    relationship_types=relationship_types,
                    config_selection=config_selection,
                    lot_number=lot_number,
                    serial_number=serial_number,
                    unit_position=unit_position,
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
                rel_props = rel.properties or {}
                norm_props = self._normalize_properties(rel_props)
                child_item = self.session.get(Item, rel.related_id) if rel.related_id else None
                parent_props = parent.properties or {}
                child_props = child_item.properties if child_item else {}
                parent_number = parent_props.get("item_number") or parent_props.get("number")
                child_number = None
                child_name = None
                if child_props:
                    child_number = child_props.get("item_number") or child_props.get("number")
                    child_name = child_props.get("name")
                parent_entry = {
                    "relationship": rel.to_dict(),
                    "parent": parent.to_dict(),
                    "child": child_item.to_dict() if child_item else None,
                    "line": self._line_fields(rel_props),
                    "line_normalized": self._line_fields_normalized(norm_props),
                    "level": _current_level + 1,
                    "parent_number": parent_number,
                    "parent_name": parent_props.get("name"),
                    "child_number": child_number,
                    "child_name": child_name,
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

    def get_bom_for_version(
        self,
        version_id: str,
        levels: int = 10,
        include_substitutes: bool = False,
        relationship_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
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

        return self.get_bom_structure(
            ver.item_id,
            levels,
            effective_date=target_date,
            include_substitutes=include_substitutes,
            relationship_types=relationship_types,
        )

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
        config_condition: Optional[Any] = None,
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
            config_condition: Variant configuration condition (JSON or simple string)
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
        if config_condition is not None:
            properties["config_condition"] = config_condition
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
        relationship_types: Optional[List[str]] = None,
        config_selection: Optional[Dict[str, Any]] = None,
        lot_number: Optional[str] = None,
        serial_number: Optional[str] = None,
        unit_position: Optional[str] = None,
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
            relationship_types=relationship_types,
            config_selection=config_selection,
            lot_number=lot_number,
            serial_number=serial_number,
            unit_position=unit_position,
        )

    def compare_bom_trees(
        self,
        left_tree: Dict[str, Any],
        right_tree: Dict[str, Any],
        include_relationship_props: Optional[List[str]] = None,
        include_child_fields: bool = False,
        line_key: str = "child_config",
        include_substitutes: bool = False,
        include_effectivity: bool = False,
        aggregate_quantities: bool = False,
    ) -> Dict[str, Any]:
        """
        Compare two BOM trees and return added/removed/changed edges.
        """
        left_edges = self._flatten_tree(
            left_tree,
            include_relationship_props=include_relationship_props,
            include_child_fields=include_child_fields,
            line_key=line_key,
            include_substitutes=include_substitutes,
            include_effectivity=include_effectivity,
            aggregate_quantities=aggregate_quantities,
        )
        right_edges = self._flatten_tree(
            right_tree,
            include_relationship_props=include_relationship_props,
            include_child_fields=include_child_fields,
            line_key=line_key,
            include_substitutes=include_substitutes,
            include_effectivity=include_effectivity,
            aggregate_quantities=aggregate_quantities,
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
        severity_counts = {"major": 0, "minor": 0, "info": 0}
        changed: List[Dict[str, Any]] = []
        for key in changed_keys:
            entry = self._format_changed_entry(left_edges[key], right_edges[key])
            severity = entry.get("severity") or "info"
            if severity in severity_counts:
                severity_counts[severity] += 1
            changed.append(entry)

        return {
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "changed": len(changed),
                "changed_major": severity_counts["major"],
                "changed_minor": severity_counts["minor"],
                "changed_info": severity_counts["info"],
            },
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    def build_delta_preview(self, compare_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert compare output into a read-only delta patch preview payload.
        """
        added = compare_result.get("added") or []
        removed = compare_result.get("removed") or []
        changed = compare_result.get("changed") or []

        operations: List[Dict[str, Any]] = []

        for entry in added:
            operations.append(
                {
                    "op": "add",
                    "line_key": entry.get("line_key"),
                    "parent_id": entry.get("parent_id"),
                    "child_id": entry.get("child_id"),
                    "relationship_id": entry.get("relationship_id"),
                    "risk_level": "medium",
                    "properties": entry.get("properties") or {},
                }
            )

        for entry in removed:
            operations.append(
                {
                    "op": "remove",
                    "line_key": entry.get("line_key"),
                    "parent_id": entry.get("parent_id"),
                    "child_id": entry.get("child_id"),
                    "relationship_id": entry.get("relationship_id"),
                    "risk_level": "medium",
                    "properties": entry.get("properties") or {},
                }
            )

        for entry in changed:
            field_changes = []
            field_severity_counts = {"major": 0, "minor": 0, "info": 0}
            for field_diff in entry.get("changes") or []:
                severity = field_diff.get("severity") or "info"
                if severity not in field_severity_counts:
                    severity = "info"
                field_severity_counts[severity] += 1
                field_changes.append(
                    {
                        "field": field_diff.get("field"),
                        "before": field_diff.get("left"),
                        "after": field_diff.get("right"),
                        "severity": severity,
                    }
                )
            op_severity = entry.get("severity") or "info"
            if op_severity not in {"major", "minor", "info"}:
                op_severity = "info"
            operations.append(
                {
                    "op": "update",
                    "line_key": entry.get("line_key"),
                    "parent_id": entry.get("parent_id"),
                    "child_id": entry.get("child_id"),
                    "relationship_id": entry.get("relationship_id"),
                    "severity": op_severity,
                    "risk_level": (
                        "high"
                        if op_severity == "major"
                        else "medium"
                        if op_severity == "minor"
                        else "low"
                    ),
                    "changes": field_changes,
                    "change_count": len(field_changes),
                    "field_severity_counts": field_severity_counts,
                }
            )

        severity_counts = {"major": 0, "minor": 0, "info": 0}
        for op in operations:
            severity = str(op.get("severity") or "info").lower()
            if severity not in severity_counts:
                severity = "info"
            severity_counts[severity] += 1
        risk_distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}
        for op in operations:
            risk = str(op.get("risk_level") or "none").lower()
            if risk not in risk_distribution:
                risk = "none"
            risk_distribution[risk] += 1

        structural_ops = len(added) + len(removed)
        update_ops = len(changed)
        if severity_counts["major"] > 0 and structural_ops >= 10:
            risk_level = "critical"
        elif severity_counts["major"] > 0 or structural_ops >= 8:
            risk_level = "high"
        elif severity_counts["minor"] > 0 or update_ops > 0:
            risk_level = "medium"
        elif structural_ops > 0:
            risk_level = "low"
        else:
            risk_level = "none"

        change_summary = {
            "ops": {
                "adds": len(added),
                "removes": len(removed),
                "updates": len(changed),
                "structural": structural_ops,
            },
            "severity": severity_counts,
            "risk_level": risk_level,
            "risk_distribution": risk_distribution,
        }
        summary = {
            "total_ops": len(operations),
            "adds": len(added),
            "removes": len(removed),
            "updates": len(changed),
            "risk_level": risk_level,
            "risk_distribution": risk_distribution,
        }
        return {
            "summary": summary,
            "change_summary": change_summary,
            "operations": operations,
        }

    @classmethod
    def normalize_delta_export_fields(
        cls, fields: Optional[List[str]]
    ) -> List[str]:
        if not fields:
            return list(cls.DELTA_EXPORT_FIELDS)
        normalized: List[str] = []
        allowed = set(cls.DELTA_EXPORT_FIELDS)
        for field in fields:
            key = str(field or "").strip()
            if not key:
                continue
            if key not in allowed:
                allowed_text = ", ".join(cls.DELTA_EXPORT_FIELDS)
                raise ValueError(f"fields contains unsupported key '{key}'. Allowed: {allowed_text}")
            if key not in normalized:
                normalized.append(key)
        if not normalized:
            return list(cls.DELTA_EXPORT_FIELDS)
        return normalized

    def filter_delta_preview_fields(
        self, delta_preview: Dict[str, Any], fields: Optional[List[str]]
    ) -> Dict[str, Any]:
        selected = self.normalize_delta_export_fields(fields)
        selected_set = set(selected)
        operations = []
        for op in delta_preview.get("operations") or []:
            if not isinstance(op, dict):
                continue
            row: Dict[str, Any] = {}
            for key in selected:
                if key in {"field", "before", "after"}:
                    continue
                if key == "change_count":
                    row["change_count"] = int(
                        op.get("change_count")
                        if op.get("change_count") is not None
                        else len(op.get("changes") or [])
                    )
                    continue
                row[key] = op.get(key)
            if "field" in selected_set or "before" in selected_set or "after" in selected_set:
                changes = op.get("changes") or []
                if not changes:
                    entry = dict(row)
                    if "field" in selected_set:
                        entry["field"] = None
                    if "before" in selected_set:
                        entry["before"] = None
                    if "after" in selected_set:
                        entry["after"] = None
                    operations.append(entry)
                else:
                    for change in changes:
                        if not isinstance(change, dict):
                            continue
                        entry = dict(row)
                        if "field" in selected_set:
                            entry["field"] = change.get("field")
                        if "before" in selected_set:
                            entry["before"] = change.get("before")
                        if "after" in selected_set:
                            entry["after"] = change.get("after")
                        operations.append(entry)
            else:
                operations.append(row)

        result = dict(delta_preview)
        result["selected_fields"] = selected
        result["operations"] = operations
        return result

    def export_delta_csv(
        self, delta_preview: Dict[str, Any], fields: Optional[List[str]] = None
    ) -> str:
        """
        Export delta preview operations as CSV text.
        """
        selected_fields = self.normalize_delta_export_fields(fields)
        selected = set(selected_fields)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=selected_fields,
        )
        writer.writeheader()

        for op in delta_preview.get("operations") or []:
            base = {
                "op": op.get("op"),
                "line_key": op.get("line_key"),
                "parent_id": op.get("parent_id"),
                "child_id": op.get("child_id"),
                "relationship_id": op.get("relationship_id"),
                "severity": op.get("severity") or "",
                "risk_level": op.get("risk_level") or "",
                "change_count": int(
                    op.get("change_count")
                    if op.get("change_count") is not None
                    else len(op.get("changes") or [])
                ),
                "properties": json.dumps(op.get("properties") or {}, ensure_ascii=False),
            }
            if op.get("op") != "update":
                writer.writerow(
                    {
                        key: (
                            ""
                            if key in {"field", "before", "after"} and key in selected
                            else base.get(key, "")
                        )
                        for key in selected_fields
                    }
                )
                continue

            changes = op.get("changes") or []
            if not changes:
                writer.writerow(
                    {
                        key: (
                            ""
                            if key in {"field", "before", "after"} and key in selected
                            else base.get(key, "")
                        )
                        for key in selected_fields
                    }
                )
                continue

            for change in changes:
                row = dict(base)
                row["field"] = change.get("field")
                row["before"] = json.dumps(change.get("before"), ensure_ascii=False)
                row["after"] = json.dumps(change.get("after"), ensure_ascii=False)
                writer.writerow({key: row.get(key, "") for key in selected_fields})

        return output.getvalue()

    def export_delta_markdown(
        self, delta_preview: Dict[str, Any], fields: Optional[List[str]] = None
    ) -> str:
        """
        Export delta preview operations as Markdown text with summary.
        """
        filtered = (
            dict(delta_preview)
            if isinstance(delta_preview.get("selected_fields"), list)
            else self.filter_delta_preview_fields(delta_preview, fields)
        )
        selected_fields = filtered.get("selected_fields")
        if not isinstance(selected_fields, list) or not selected_fields:
            selected_fields = self.normalize_delta_export_fields(fields)
        operations = filtered.get("operations")
        if not isinstance(operations, list):
            operations = []

        summary = filtered.get("summary") if isinstance(filtered.get("summary"), dict) else {}
        change_summary = (
            filtered.get("change_summary")
            if isinstance(filtered.get("change_summary"), dict)
            else {}
        )
        compare_summary = (
            filtered.get("compare_summary")
            if isinstance(filtered.get("compare_summary"), dict)
            else {}
        )

        def _as_cell(value: Any) -> str:
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

        lines = [
            "# BOM Delta Preview",
            "",
            "## Summary",
            f"- total_ops: {summary.get('total_ops') or 0}",
            f"- adds: {summary.get('adds') or 0}",
            f"- removes: {summary.get('removes') or 0}",
            f"- updates: {summary.get('updates') or 0}",
            f"- risk_level: {summary.get('risk_level') or 'none'}",
            (
                f"- risk_distribution: "
                f"{json.dumps(summary.get('risk_distribution') or {}, ensure_ascii=False)}"
            ),
            (
                f"- change_summary: "
                f"{json.dumps(change_summary, ensure_ascii=False)}"
            ),
            (
                f"- compare_summary: "
                f"{json.dumps(compare_summary, ensure_ascii=False)}"
            ),
            "",
            "## Operations",
        ]

        if not operations:
            lines.append("")
            lines.append("_No operations_")
            lines.append("")
            return "\n".join(lines)

        header = "| " + " | ".join(selected_fields) + " |"
        sep = "| " + " | ".join("---" for _ in selected_fields) + " |"
        lines.extend(["", header, sep])

        for op in operations:
            if not isinstance(op, dict):
                continue
            row = "| " + " | ".join(_as_cell(op.get(key)) for key in selected_fields) + " |"
            lines.append(row)

        lines.append("")
        return "\n".join(lines)

    def _flatten_tree(
        self,
        tree: Dict[str, Any],
        include_relationship_props: Optional[List[str]] = None,
        include_child_fields: bool = False,
        line_key: str = "child_config",
        include_substitutes: bool = False,
        include_effectivity: bool = False,
        aggregate_quantities: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        edges: Dict[str, Dict[str, Any]] = {}
        effectivity_cache: Dict[str, List[Dict[str, Any]]] = {}
        substitute_cache: Dict[str, List[Dict[str, Any]]] = {}
        sub_service = None
        if include_substitutes:
            from .substitute_service import SubstituteService

            sub_service = SubstituteService(self.session)

        def walk(node: Dict[str, Any], path: List[Dict[str, Any]]) -> None:
            parent_id = node.get("id")
            parent_config_id = node.get("config_id") or parent_id
            parent_path = path + [self._build_path_node(node)]
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
                rel_id = rel.get("id")
                if include_effectivity and rel_id:
                    effectivities = effectivity_cache.get(rel_id)
                    if effectivities is None:
                        effectivities = self._serialize_effectivities(rel_id)
                        effectivity_cache[rel_id] = effectivities
                    raw_props["effectivities"] = effectivities
                if include_substitutes and rel_id:
                    substitutes = substitute_cache.get(rel_id)
                    if substitutes is None:
                        existing = child_entry.get("substitutes")
                        if existing is None and sub_service:
                            existing = sub_service.get_bom_substitutes(rel_id)
                        substitutes = self._serialize_substitutes(existing or [])
                        substitute_cache[rel_id] = substitutes
                    raw_props["substitutes"] = substitutes
                norm_props = self._normalize_properties(raw_props)

                key = self._build_line_key(
                    line_key,
                    parent_id=parent_id,
                    child_id=child_id,
                    parent_config_id=parent_config_id,
                    child_config_id=child_config_id,
                    relationship_id=rel_id,
                    normalized_properties=norm_props,
                )
                entry: Dict[str, Any] = {
                    "parent_id": parent_id,
                    "child_id": child_id,
                    "parent_config_id": parent_config_id,
                    "child_config_id": child_config_id,
                    "relationship_id": rel_id,
                    "line_key": key,
                    "path": parent_path + [self._build_path_node(child)],
                    "level": len(parent_path),
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

                if aggregate_quantities and key in edges:
                    existing = edges[key]
                    existing_props = existing.get("properties") or {}
                    existing_norm = existing.get("normalized_properties") or {}

                    combined_qty = self._sum_quantities(
                        existing_norm.get("quantity"),
                        norm_props.get("quantity"),
                    )
                    combined_uom = self._merge_uom(
                        existing_norm.get("uom"),
                        norm_props.get("uom"),
                    )

                    if combined_qty is not None:
                        existing_norm["quantity"] = combined_qty
                        existing_props["quantity"] = combined_qty
                    if combined_uom:
                        existing_norm["uom"] = combined_uom
                        existing_props["uom"] = combined_uom

                    existing["normalized_properties"] = existing_norm
                    existing["properties"] = existing_props
                    edges[key] = existing
                else:
                    edges[key] = entry
                walk(child, parent_path)

        walk(tree, [])
        return edges

    def _build_path_node(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "config_id": item.get("config_id"),
            "item_number": item.get("item_number"),
            "name": item.get("name"),
        }

    def _build_line_key(
        self,
        line_key: str,
        *,
        parent_id: Optional[str],
        child_id: Optional[str],
        parent_config_id: Optional[str],
        child_config_id: Optional[str],
        relationship_id: Optional[str],
        normalized_properties: Dict[str, Any],
    ) -> str:
        key = (line_key or "child_config").strip().lower()
        parent_fallback = parent_config_id or parent_id or ""
        child_fallback = child_config_id or child_id or ""
        find_num = normalized_properties.get("find_num")
        refdes = self._format_key_list(normalized_properties.get("refdes"))
        eff_key = normalized_properties.get("effectivities")
        qty_key = self._format_key_number(normalized_properties.get("quantity"))
        if eff_key:
            eff_value = self._format_key_list(eff_key)
        else:
            eff_from = normalized_properties.get("effectivity_from")
            eff_to = normalized_properties.get("effectivity_to")
            eff_value = f"{eff_from or ''}-{eff_to or ''}"

        if key in {"child_id", "item_id"}:
            return f"{parent_id or parent_fallback}::{child_id or child_fallback}"
        if key in {"child_config", "config"}:
            return f"{parent_fallback}::{child_fallback}"
        if key in {"relationship_id", "line_id", "rel_id"}:
            return relationship_id or f"{parent_id or parent_fallback}::{child_id or child_fallback}"
        if key in {"child_id_find_num", "child_id_find"}:
            return f"{parent_id or parent_fallback}::{child_id or child_fallback}::{find_num or ''}"
        if key in {"child_config_find_num", "child_config_find"}:
            return f"{parent_fallback}::{child_fallback}::{find_num or ''}"
        if key in {"child_id_refdes", "child_id_ref"}:
            return f"{parent_id or parent_fallback}::{child_id or child_fallback}::{refdes}"
        if key in {"child_config_refdes", "child_config_ref"}:
            return f"{parent_fallback}::{child_fallback}::{refdes}"
        if key in {"child_id_find_refdes", "child_id_find_ref"}:
            return (
                f"{parent_id or parent_fallback}::{child_id or child_fallback}"
                f"::{find_num or ''}::{refdes}"
            )
        if key in {"child_config_find_refdes", "child_config_find_ref"}:
            return (
                f"{parent_fallback}::{child_fallback}"
                f"::{find_num or ''}::{refdes}"
            )
        if key in {"child_id_find_num_qty", "child_id_find_qty"}:
            return (
                f"{parent_id or parent_fallback}::{child_id or child_fallback}"
                f"::{find_num or ''}::{qty_key}"
            )
        if key in {"child_config_find_num_qty", "child_config_find_qty"}:
            return (
                f"{parent_fallback}::{child_fallback}"
                f"::{find_num or ''}::{qty_key}"
            )
        if key in {"line_full", "full"}:
            return (
                f"{parent_id or parent_fallback}::{child_id or child_fallback}"
                f"::{find_num or ''}::{refdes}::{eff_value}"
            )
        return f"{parent_fallback}::{child_fallback}"

    def _format_key_list(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            return ",".join(str(v) for v in value)
        return str(value)

    def _format_key_number(self, value: Any) -> str:
        if value is None:
            return ""
        try:
            return str(Decimal(str(value)).normalize())
        except (InvalidOperation, ValueError):
            return str(value)

    def _sum_quantities(self, left: Any, right: Any) -> Optional[float]:
        if left is None:
            return float(right) if right is not None else None
        if right is None:
            return float(left) if left is not None else None
        try:
            return float(Decimal(str(left)) + Decimal(str(right)))
        except (InvalidOperation, ValueError, TypeError):
            try:
                return float(left) + float(right)
            except (TypeError, ValueError):
                return float(right) if right is not None else float(left)

    def _merge_uom(self, left: Any, right: Any) -> Optional[str]:
        left_val = str(left).strip().upper() if left else ""
        right_val = str(right).strip().upper() if right else ""
        if not left_val:
            return right_val or None
        if not right_val:
            return left_val or None
        if left_val == right_val:
            return left_val
        return "MIXED"

    def _serialize_effectivities(self, item_id: str) -> List[Dict[str, Any]]:
        effectivities = self.eff_service.get_item_effectivities(item_id)
        entries: List[Dict[str, Any]] = []
        for eff in effectivities:
            entries.append(
                {
                    "type": eff.effectivity_type,
                    "start_date": eff.start_date.isoformat() if eff.start_date else None,
                    "end_date": eff.end_date.isoformat() if eff.end_date else None,
                    "payload": eff.payload or {},
                }
            )
        return entries

    def _serialize_substitutes(
        self, substitutes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        for entry in substitutes or []:
            if not isinstance(entry, dict):
                continue
            rel = entry.get("relationship") or {}
            rel_props = rel.get("properties") or {}
            sub_part = entry.get("substitute_part") or entry.get("part") or {}
            sub_id = sub_part.get("id") or rel.get("related_id")
            if not sub_id:
                continue
            entries.append(
                {
                    "item_id": sub_id,
                    "rank": rel_props.get("rank") or entry.get("rank"),
                    "note": rel_props.get("note"),
                }
            )
        return entries

    def _select_relationship_properties(
        self,
        relationship: Dict[str, Any],
        include_relationship_props: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        props = relationship.get("properties") or {}
        if include_relationship_props is not None:
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

    def _line_field_keys(self) -> tuple[str, ...]:
        return self.LINE_FIELD_KEYS

    def _line_fields(self, props: Dict[str, Any]) -> Dict[str, Any]:
        return {key: props.get(key) for key in self._line_field_keys()}

    def _jsonify_value(self, value: Any) -> Any:
        if isinstance(value, tuple):
            return [self._jsonify_value(item) for item in value]
        if isinstance(value, list):
            return [self._jsonify_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self._jsonify_value(item) for key, item in value.items()}
        return value

    def _line_fields_normalized(self, props: Dict[str, Any]) -> Dict[str, Any]:
        return self._jsonify_value(self._line_fields(props))

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
        if key == "substitutes":
            return self._normalize_substitutes(value)
        if key == "effectivities":
            return self._normalize_effectivities(value)
        if key in {"effectivity_from", "effectivity_to"}:
            return self._normalize_datetime(value)
        if key == "config_condition":
            return self._normalize_config_condition(value) or value
        return value

    def _match_config_condition(
        self, condition: Any, selection: Dict[str, Any]
    ) -> bool:
        if not selection:
            return True
        if condition is None:
            return True
        normalized = self._normalize_config_condition(condition)
        if normalized is None:
            return False
        return self._evaluate_config_condition(normalized, selection)

    def _normalize_config_condition(self, condition: Any) -> Optional[Dict[str, Any]]:
        if isinstance(condition, dict):
            return condition
        if isinstance(condition, str):
            raw = condition.strip()
            if not raw:
                return None
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return self._parse_simple_condition(raw)
        return None

    def _parse_simple_condition(self, expr: str) -> Optional[Dict[str, Any]]:
        parts = [p.strip() for p in re.split(r"[;,]+", expr) if p.strip()]
        conds: List[Dict[str, Any]] = []
        op_map = {
            "=": "eq",
            "!=": "ne",
            ">": "gt",
            "<": "lt",
            ">=": "gte",
            "<=": "lte",
            "~": "regex",
        }
        for part in parts:
            match = re.match(r"^([^=!<>~]+)(!=|>=|<=|=|>|<|~)(.+)$", part)
            if not match:
                continue
            key, op, value = match.groups()
            key = key.strip()
            value = value.strip()
            if key and value:
                entry: Dict[str, Any] = {"option": key, "value": value}
                mapped = op_map.get(op)
                if mapped and mapped != "eq":
                    entry["op"] = mapped
                conds.append(entry)
        if not conds:
            return None
        if len(conds) == 1:
            return conds[0]
        return {"all": conds}

    def _get_selection_value(self, selection: Dict[str, Any], key: str) -> Any:
        if key in selection:
            return selection[key]
        lowered = {str(k).lower(): v for k, v in selection.items()}
        return lowered.get(str(key).lower())

    def _normalize_selection_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            for field in ("value", "key", "id"):
                if field in value:
                    return value.get(field)
            return value
        if isinstance(value, list):
            return [self._normalize_selection_value(item) for item in value]
        return value

    def _has_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) > 0
        if isinstance(value, str):
            return bool(value.strip())
        return True

    def _coerce_number(self, value: Any) -> Optional[Decimal]:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _evaluate_config_condition(self, condition: Dict[str, Any], selection: Dict[str, Any]) -> bool:
        if not condition:
            return True
        if "all" in condition:
            items = condition.get("all") or []
            return all(self._evaluate_config_condition(c, selection) for c in items)
        if "any" in condition:
            items = condition.get("any") or []
            return any(self._evaluate_config_condition(c, selection) for c in items)
        if "not" in condition:
            return not self._evaluate_config_condition(condition.get("not") or {}, selection)

        option_key = (
            condition.get("option")
            or condition.get("option_set")
            or condition.get("key")
        )
        if not option_key:
            return False

        selected = self._get_selection_value(selection, str(option_key))
        selected = self._normalize_selection_value(selected)

        if "missing" in condition:
            return not self._has_value(selected) if condition.get("missing") else self._has_value(selected)
        if "exists" in condition:
            return self._has_value(selected) if condition.get("exists") else not self._has_value(selected)

        op = condition.get("op") or condition.get("operator") or condition.get("cmp") or "eq"
        op = str(op).strip().lower()

        values = None
        if "value" in condition:
            values = condition.get("value")
        if values is None and "values" in condition:
            values = condition.get("values")
        if values is None and "in" in condition:
            values = condition.get("in")

        if op in {"between", "range"}:
            values = condition.get("range") or condition.get("between")
        min_value = condition.get("min")
        max_value = condition.get("max")

        def iter_selected(value: Any) -> List[Any]:
            if isinstance(value, (list, tuple, set)):
                return list(value)
            return [value]

        def match_scalar(sel: Any, target: Any) -> bool:
            if op in {"contains", "has", "includes"}:
                if isinstance(sel, (list, tuple, set)):
                    return target in sel
                return str(target) in str(sel)
            if op in {"regex", "match"}:
                try:
                    return re.search(str(target), str(sel)) is not None
                except re.error:
                    return False

            left_num = self._coerce_number(sel)
            right_num = self._coerce_number(target)
            if left_num is not None and right_num is not None:
                if op in {"gt", ">"}:
                    return left_num > right_num
                if op in {"gte", ">="}:
                    return left_num >= right_num
                if op in {"lt", "<"}:
                    return left_num < right_num
                if op in {"lte", "<="}:
                    return left_num <= right_num
                if op in {"ne", "!="}:
                    return left_num != right_num
                return left_num == right_num

            if op in {"gt", ">"}:
                return str(sel) > str(target)
            if op in {"gte", ">="}:
                return str(sel) >= str(target)
            if op in {"lt", "<"}:
                return str(sel) < str(target)
            if op in {"lte", "<="}:
                return str(sel) <= str(target)
            if op in {"ne", "!="}:
                return str(sel) != str(target)
            return str(sel) == str(target)

        def match_values(sel: Any, target_values: Any) -> bool:
            if op in {"in", "not_in"}:
                target_list = target_values if isinstance(target_values, (list, tuple, set)) else [target_values]
                in_result = sel in target_list
                return not in_result if op == "not_in" else in_result
            return match_scalar(sel, target_values)

        if not self._has_value(selected):
            return False

        if op in {"between", "range"}:
            range_values = values if isinstance(values, (list, tuple)) and len(values) >= 2 else None
            if range_values is None and (min_value is not None or max_value is not None):
                range_values = [min_value, max_value]
            if range_values is None:
                return False
            low, high = range_values[0], range_values[1]
            for sel in iter_selected(selected):
                sel_num = self._coerce_number(sel)
                low_num = self._coerce_number(low)
                high_num = self._coerce_number(high)
                if sel_num is None or low_num is None or high_num is None:
                    if str(low) <= str(sel) <= str(high):
                        return True
                else:
                    if low_num <= sel_num <= high_num:
                        return True
            return False

        if op in {"in", "not_in"}:
            return any(match_values(sel, values) for sel in iter_selected(selected))

        if values is None:
            return self._has_value(selected)

        if isinstance(values, (list, tuple, set)):
            return any(match_values(sel, v) for sel in iter_selected(selected) for v in values)

        return any(match_values(sel, values) for sel in iter_selected(selected))

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

    def _normalize_substitutes(self, value: Any) -> tuple:
        entries = []
        for entry in value or []:
            if isinstance(entry, dict):
                item_id = entry.get("item_id") or entry.get("id") or ""
                rank = entry.get("rank")
                note = entry.get("note")
                entries.append((str(item_id), str(rank or ""), str(note or "")))
            else:
                entries.append((str(entry), "", ""))
        return tuple(sorted(entries))

    def _normalize_effectivities(self, value: Any) -> tuple:
        entries = []
        for entry in value or []:
            if not isinstance(entry, dict):
                continue
            eff_type = entry.get("type") or entry.get("effectivity_type") or ""
            start_date = self._normalize_datetime(entry.get("start_date"))
            end_date = self._normalize_datetime(entry.get("end_date"))
            payload = entry.get("payload") or {}
            if isinstance(payload, dict):
                payload_key = json.dumps(payload, sort_keys=True)
            else:
                payload_key = str(payload)
            entries.append((str(eff_type), str(start_date or ""), str(end_date or ""), payload_key))
        return tuple(sorted(entries))

    @classmethod
    def field_severity(cls, field: str) -> str:
        if field in cls.MAJOR_FIELDS:
            return "major"
        if field in cls.MINOR_FIELDS:
            return "minor"
        return "info"

    def _field_severity(self, field: str) -> str:
        return self.field_severity(field)

    def _severity_rank(self, severity: str) -> int:
        order = {"info": 0, "minor": 1, "major": 2}
        return order.get(severity, 0)

    def _summarize_severity(self, diffs: List[Dict[str, Any]]) -> str:
        if not diffs:
            return "info"
        highest = "info"
        for diff in diffs:
            severity = diff.get("severity") or "info"
            if self._severity_rank(severity) > self._severity_rank(highest):
                highest = severity
        return highest

    def _build_field_diffs(
        self,
        left_entry: Dict[str, Any],
        right_entry: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        left_props = left_entry.get("properties") or {}
        right_props = right_entry.get("properties") or {}
        left_norm = left_entry.get("normalized_properties") or {}
        right_norm = right_entry.get("normalized_properties") or {}

        diffs: List[Dict[str, Any]] = []
        for key in sorted(set(left_norm.keys()) | set(right_norm.keys())):
            left_val = left_norm.get(key)
            right_val = right_norm.get(key)
            if key == "quantity" and left_val is not None and right_val is not None:
                try:
                    if abs(float(left_val) - float(right_val)) <= 1e-6:
                        continue
                except (TypeError, ValueError):
                    pass
            if left_val == right_val:
                continue
            diffs.append(
                {
                    "field": key,
                    "left": left_props.get(key),
                    "right": right_props.get(key),
                    "normalized_left": left_val,
                    "normalized_right": right_val,
                    "severity": self._field_severity(key),
                }
            )
        return diffs

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
        props = entry.get("properties") or {}
        norm_props = entry.get("normalized_properties") or {}
        result = {
            "parent_id": entry.get("parent_id"),
            "child_id": entry.get("child_id"),
            "relationship_id": entry.get("relationship_id"),
            "line_key": entry.get("line_key"),
            "parent_config_id": entry.get("parent_config_id"),
            "child_config_id": entry.get("child_config_id"),
            "level": entry.get("level"),
            "path": entry.get("path"),
            "properties": props,
            "line": self._line_fields(props),
            "line_normalized": self._line_fields_normalized(norm_props),
        }
        parent = entry.get("parent") or {}
        child = entry.get("child") or {}
        if parent:
            result["parent"] = parent
            result["parent_number"] = parent.get("item_number")
            result["parent_name"] = parent.get("name")
        if child:
            result["child"] = child
            result["child_number"] = child.get("item_number")
            result["child_name"] = child.get("name")
        return result

    def _format_changed_entry(
        self,
        left_entry: Dict[str, Any],
        right_entry: Dict[str, Any],
    ) -> Dict[str, Any]:

        diffs = self._build_field_diffs(left_entry, right_entry)
        before = {d["field"]: d["left"] for d in diffs}
        after = {d["field"]: d["right"] for d in diffs}
        severity = self._summarize_severity(diffs)
        left_props = left_entry.get("properties") or {}
        right_props = right_entry.get("properties") or {}
        left_norm = left_entry.get("normalized_properties") or {}
        right_norm = right_entry.get("normalized_properties") or {}

        result = {
            "parent_id": left_entry.get("parent_id"),
            "child_id": left_entry.get("child_id"),
            "relationship_id": left_entry.get("relationship_id"),
            "line_key": left_entry.get("line_key"),
            "parent_config_id": left_entry.get("parent_config_id"),
            "child_config_id": left_entry.get("child_config_id"),
            "level": left_entry.get("level"),
            "path": left_entry.get("path"),
            "before": before,
            "after": after,
            "before_line": self._line_fields(left_props),
            "after_line": self._line_fields(right_props),
            "before_normalized": self._line_fields_normalized(left_norm),
            "after_normalized": self._line_fields_normalized(right_norm),
            "changes": diffs,
            "severity": severity,
        }
        parent = left_entry.get("parent") or {}
        child = left_entry.get("child") or {}
        if parent:
            result["parent"] = parent
            result["parent_number"] = parent.get("item_number")
            result["parent_name"] = parent.get("name")
        if child:
            result["child"] = child
            result["child_number"] = child.get("item_number")
            result["child_name"] = child.get("name")
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
