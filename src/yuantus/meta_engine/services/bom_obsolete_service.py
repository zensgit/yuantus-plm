from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from yuantus.meta_engine.lifecycle.guard import get_lifecycle_state
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.effectivity_service import EffectivityService


class BOMObsoleteService:
    """Detect and resolve obsolete BOM lines."""

    DEFAULT_REL_TYPES = ("Part BOM", "Manufacturing BOM")
    REPLACEMENT_KEYS = ("replacement_id", "superseded_by")

    def __init__(self, session: Session):
        self.session = session
        self.effectivity = EffectivityService(session)

    def scan(
        self,
        root_item_id: str,
        *,
        recursive: bool = True,
        max_levels: int = 10,
        relationship_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        rel_types = relationship_types or list(self.DEFAULT_REL_TYPES)
        lines = self._collect_lines(
            root_item_id,
            recursive=recursive,
            max_levels=max_levels,
            relationship_types=rel_types,
        )
        entries: List[Dict[str, Any]] = []
        for line in lines:
            rel = line["relationship"]
            parent = line["parent"]
            child = line["child"]
            reasons: List[str] = []
            if child is None:
                reasons.append("missing_child")
            else:
                if not child.is_current:
                    reasons.append("not_current")
                if self._is_obsolete_state(child):
                    reasons.append("obsolete_state")
            if not reasons:
                continue

            replacement = self._find_replacement(child) if child else None

            entry = {
                "relationship_id": rel.id,
                "relationship_type": rel.item_type_id,
                "parent_id": parent.id if parent else None,
                "parent_number": self._item_number(parent),
                "parent_name": self._item_name(parent),
                "child_id": child.id if child else None,
                "child_number": self._item_number(child),
                "child_name": self._item_name(child),
                "child_state": child.state if child else None,
                "child_is_current": child.is_current if child else None,
                "replacement_id": replacement.id if replacement else None,
                "replacement_number": self._item_number(replacement),
                "replacement_name": self._item_name(replacement),
                "level": line["level"],
                "reasons": reasons,
            }
            entries.append(entry)

        return {
            "root_id": root_item_id,
            "count": len(entries),
            "entries": entries,
        }

    def resolve(
        self,
        root_item_id: str,
        *,
        mode: str = "update",
        recursive: bool = True,
        max_levels: int = 10,
        relationship_types: Optional[List[str]] = None,
        dry_run: bool = False,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        mode = mode.strip().lower()
        if mode not in {"update", "new_bom"}:
            raise ValueError("mode must be 'update' or 'new_bom'")

        rel_types = relationship_types or list(self.DEFAULT_REL_TYPES)
        scan = self.scan(
            root_item_id,
            recursive=recursive,
            max_levels=max_levels,
            relationship_types=rel_types,
        )
        entries = scan["entries"]

        result_entries: List[Dict[str, Any]] = []
        updated_lines = 0
        created_lines = 0
        skipped_locked = 0
        unresolved = 0
        touched_parents: set[str] = set()

        locked_cache: Dict[str, Tuple[bool, Optional[str]]] = {}

        def parent_locked(parent_id: Optional[str]) -> Tuple[bool, Optional[str]]:
            if not parent_id:
                return False, None
            if parent_id in locked_cache:
                return locked_cache[parent_id]
            parent = self.session.get(Item, parent_id)
            item_type = (
                self.session.get(ItemType, parent.item_type_id) if parent else None
            )
            locked = False
            locked_state = None
            if parent and item_type:
                state = get_lifecycle_state(self.session, parent, item_type)
                if state and state.version_lock:
                    locked = True
                    locked_state = state.name
            locked_cache[parent_id] = (locked, locked_state)
            return locked, locked_state

        if dry_run:
            for entry in entries:
                entry = dict(entry)
                entry["status"] = "dry_run"
                result_entries.append(entry)
            return {
                "ok": True,
                "mode": mode,
                "dry_run": True,
                "root_id": root_item_id,
                "summary": {
                    "entries": len(entries),
                    "updated_lines": 0,
                    "created_lines": 0,
                    "skipped_locked": 0,
                    "unresolved": 0,
                    "parents_touched": 0,
                },
                "entries": result_entries,
            }

        if mode == "update":
            for entry in entries:
                entry_out = dict(entry)
                parent_id = entry.get("parent_id")
                locked, locked_state = parent_locked(parent_id)
                if locked:
                    entry_out["status"] = "skipped_locked"
                    entry_out["locked_state"] = locked_state
                    skipped_locked += 1
                    result_entries.append(entry_out)
                    continue

                replacement_id = entry.get("replacement_id")
                if not replacement_id:
                    entry_out["status"] = "unresolved"
                    unresolved += 1
                    result_entries.append(entry_out)
                    continue

                rel = self.session.get(Item, entry["relationship_id"])
                if not rel or not rel.is_current:
                    entry_out["status"] = "skipped_missing"
                    result_entries.append(entry_out)
                    continue

                rel.related_id = replacement_id
                if user_id is not None:
                    rel.modified_by_id = user_id
                updated_lines += 1
                touched_parents.add(parent_id)
                entry_out["status"] = "updated"
                result_entries.append(entry_out)

        else:
            # new_bom: clone all current lines for each touched parent
            entries_by_parent: Dict[str, List[Dict[str, Any]]] = {}
            for entry in entries:
                parent_id = entry.get("parent_id")
                if not parent_id:
                    continue
                entries_by_parent.setdefault(parent_id, []).append(entry)

            for parent_id, parent_entries in entries_by_parent.items():
                locked, locked_state = parent_locked(parent_id)
                if locked:
                    skipped_locked += len(parent_entries)
                    for entry in parent_entries:
                        entry_out = dict(entry)
                        entry_out["status"] = "skipped_locked"
                        entry_out["locked_state"] = locked_state
                        result_entries.append(entry_out)
                    continue

                replacement_map = {
                    entry["relationship_id"]: entry.get("replacement_id")
                    for entry in parent_entries
                }

                rels = (
                    self.session.query(Item)
                    .filter(
                        Item.source_id == parent_id,
                        Item.is_current.is_(True),
                        Item.item_type_id.in_(rel_types),
                    )
                    .all()
                )
                if not rels:
                    for entry in parent_entries:
                        entry_out = dict(entry)
                        entry_out["status"] = "skipped_missing"
                        result_entries.append(entry_out)
                    continue

                new_rel_ids = []
                for rel in rels:
                    new_child_id = replacement_map.get(rel.id) or rel.related_id
                    if rel.id in replacement_map and not replacement_map.get(rel.id):
                        unresolved += 1
                    new_rel = Item(
                        id=str(uuid.uuid4()),
                        item_type_id=rel.item_type_id,
                        config_id=str(uuid.uuid4()),
                        generation=1,
                        is_current=True,
                        state=rel.state,
                        properties=dict(rel.properties or {}),
                        source_id=rel.source_id,
                        related_id=new_child_id,
                        created_by_id=user_id,
                        permission_id=rel.permission_id,
                        created_at=datetime.utcnow(),
                    )
                    self.session.add(new_rel)
                    new_rel_ids.append((rel, new_rel))
                    created_lines += 1

                for rel, new_rel in new_rel_ids:
                    # Copy effectivities
                    for eff in self.effectivity.get_item_effectivities(rel.id):
                        self.effectivity.create_effectivity(
                            item_id=new_rel.id,
                            effectivity_type=eff.effectivity_type,
                            start_date=eff.start_date,
                            end_date=eff.end_date,
                            payload=eff.payload,
                            created_by_id=user_id,
                        )
                    # Copy substitutes
                    subs = (
                        self.session.query(Item)
                        .filter(
                            Item.item_type_id == "Part BOM Substitute",
                            Item.source_id == rel.id,
                            Item.is_current.is_(True),
                        )
                        .all()
                    )
                    for sub in subs:
                        new_sub = Item(
                            id=str(uuid.uuid4()),
                            item_type_id="Part BOM Substitute",
                            config_id=str(uuid.uuid4()),
                            generation=1,
                            is_current=True,
                            state=sub.state,
                            properties=dict(sub.properties or {}),
                            source_id=new_rel.id,
                            related_id=sub.related_id,
                            created_by_id=user_id,
                            permission_id=sub.permission_id,
                            created_at=datetime.utcnow(),
                        )
                        self.session.add(new_sub)

                # Mark old relationships not current
                for rel in rels:
                    rel.is_current = False
                    if user_id is not None:
                        rel.modified_by_id = user_id

                touched_parents.add(parent_id)

                for entry in parent_entries:
                    entry_out = dict(entry)
                    if entry.get("replacement_id"):
                        entry_out["status"] = "updated"
                        updated_lines += 1
                    else:
                        entry_out["status"] = "unresolved"
                    result_entries.append(entry_out)

        return {
            "ok": True,
            "mode": mode,
            "root_id": root_item_id,
            "summary": {
                "entries": len(entries),
                "updated_lines": updated_lines,
                "created_lines": created_lines,
                "skipped_locked": skipped_locked,
                "unresolved": unresolved,
                "parents_touched": len(touched_parents),
            },
            "entries": result_entries,
        }

    def _collect_lines(
        self,
        root_item_id: str,
        *,
        recursive: bool,
        max_levels: int,
        relationship_types: List[str],
    ) -> List[Dict[str, Any]]:
        if not root_item_id:
            return []
        results: List[Dict[str, Any]] = []
        queue: List[Tuple[str, int]] = [(root_item_id, 0)]
        visited: set[str] = set()

        while queue:
            parent_id, level = queue.pop(0)
            if parent_id in visited:
                continue
            visited.add(parent_id)
            parent = self.session.get(Item, parent_id)
            if not parent:
                continue

            rels = (
                self.session.query(Item)
                .filter(
                    Item.source_id == parent_id,
                    Item.is_current.is_(True),
                    Item.item_type_id.in_(relationship_types),
                )
                .all()
            )

            for rel in rels:
                child = self.session.get(Item, rel.related_id) if rel.related_id else None
                results.append(
                    {
                        "relationship": rel,
                        "parent": parent,
                        "child": child,
                        "level": level + 1,
                    }
                )
                if (
                    recursive
                    and child
                    and (max_levels < 0 or level < max_levels)
                ):
                    queue.append((child.id, level + 1))

        return results

    def _is_obsolete_state(self, item: Item) -> bool:
        if not item:
            return False
        props = item.properties or {}
        flag = props.get("obsolete")
        if isinstance(flag, bool) and flag:
            return True
        if isinstance(flag, str) and flag.strip().lower() in {"true", "1", "yes"}:
            return True
        flag = props.get("is_obsolete")
        if isinstance(flag, bool) and flag:
            return True
        if isinstance(flag, str) and flag.strip().lower() in {"true", "1", "yes"}:
            return True
        engineering_state = props.get("engineering_state")
        if isinstance(engineering_state, str) and engineering_state.strip().lower() in {
            "obsoleted",
            "obsolete",
        }:
            return True
        if item.state and item.state.strip().lower() == "obsolete":
            return True
        if item.current_state:
            state = self.session.get(ItemType, item.item_type_id)
            lifecycle_state = get_lifecycle_state(self.session, item, state)
            if lifecycle_state and lifecycle_state.is_end_state:
                return True
        return False

    def _find_replacement(self, item: Item) -> Optional[Item]:
        if not item:
            return None
        props = item.properties or {}
        for key in self.REPLACEMENT_KEYS:
            candidate_id = props.get(key)
            if candidate_id:
                candidate = self.session.get(Item, candidate_id)
                if candidate:
                    return candidate

        if not item.config_id:
            return None

        query = (
            self.session.query(Item)
            .filter(
                Item.config_id == item.config_id,
                Item.item_type_id == item.item_type_id,
                Item.id != item.id,
                Item.is_current.is_(True),
            )
            .order_by(Item.generation.desc(), Item.created_at.desc())
        )
        candidate = query.first()
        if not candidate:
            return None
        if candidate.state and candidate.state.strip().lower() == "obsolete":
            return None
        return candidate

    @staticmethod
    def _item_number(item: Optional[Item]) -> Optional[str]:
        if not item:
            return None
        props = item.properties or {}
        return props.get("item_number") or props.get("number")

    @staticmethod
    def _item_name(item: Optional[Item]) -> Optional[str]:
        if not item:
            return None
        props = item.properties or {}
        return props.get("name")
