from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.baseline import Baseline
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.effectivity_service import EffectivityService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService


class BaselineService:
    def __init__(self, session: Session):
        self.session = session
        self.bom_service = BOMService(session)
        self.permission_service = MetaPermissionService(session)
        self.effectivity_service = EffectivityService(session)

    def _normalize_effective_at(self, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        return EffectivityService._normalize_utc_naive(value)

    def _resolve_root(
        self, root_item_id: Optional[str], root_version_id: Optional[str]
    ) -> Tuple[Item, Optional[str]]:
        if root_version_id:
            from yuantus.meta_engine.version.models import ItemVersion

            ver = self.session.get(ItemVersion, root_version_id)
            if not ver:
                raise ValueError(f"Version {root_version_id} not found")
            item = self.session.get(Item, ver.item_id)
            if not item:
                raise ValueError(f"Item {ver.item_id} not found")
            return item, ver.id

        if not root_item_id:
            raise ValueError("root_item_id or root_version_id required")
        item = self.session.get(Item, root_item_id)
        if not item:
            raise ValueError(f"Item {root_item_id} not found")
        return item, None

    def _ensure_can_read(self, item: Item, user_id: str, roles: List[str]) -> None:
        allowed = self.permission_service.check_permission(
            item.item_type_id,
            AMLAction.get,
            user_id,
            roles,
            item_state=item.state,
            item_owner_id=str(item.created_by_id) if item.created_by_id else None,
        )
        if not allowed:
            raise PermissionError(action=AMLAction.get.value, resource=item.item_type_id)

    def _count_tree(self, node: Dict[str, Any]) -> Tuple[int, int]:
        item_count = 1
        rel_count = 0
        for child in node.get("children", []) or []:
            rel_count += 1
            child_node = child.get("child") or {}
            sub_items, sub_rels = self._count_tree(child_node)
            item_count += sub_items
            rel_count += sub_rels
        return item_count, rel_count

    def _attach_effectivities(self, node: Dict[str, Any]) -> None:
        for child in node.get("children", []) or []:
            rel = child.get("relationship") or {}
            rel_id = rel.get("id")
            if rel_id:
                props = rel.get("properties") or {}
                props["effectivities"] = [
                    {
                        "type": eff.effectivity_type,
                        "start_date": eff.start_date.isoformat() if eff.start_date else None,
                        "end_date": eff.end_date.isoformat() if eff.end_date else None,
                        "payload": eff.payload or {},
                    }
                    for eff in self.effectivity_service.get_item_effectivities(rel_id)
                ]
                rel["properties"] = props
                child["relationship"] = rel
            self._attach_effectivities(child.get("child") or {})

    def create_baseline(
        self,
        *,
        name: str,
        description: Optional[str],
        root_item_id: Optional[str],
        root_version_id: Optional[str],
        max_levels: int,
        effective_at: Optional[datetime],
        include_substitutes: bool,
        include_effectivity: bool,
        line_key: str,
        created_by_id: Optional[int],
        roles: List[str],
    ) -> Baseline:
        item, resolved_version_id = self._resolve_root(root_item_id, root_version_id)
        self._ensure_can_read(item, str(created_by_id or "guest"), roles)

        effective_at = self._normalize_effective_at(effective_at)
        if resolved_version_id:
            snapshot = self.bom_service.get_bom_for_version(
                resolved_version_id, levels=max_levels, include_substitutes=include_substitutes
            )
        else:
            snapshot = self.bom_service.get_bom_structure(
                item.id,
                levels=max_levels,
                effective_date=effective_at,
                include_substitutes=include_substitutes,
            )

        if include_effectivity:
            self._attach_effectivities(snapshot)

        item_count, rel_count = self._count_tree(snapshot)

        baseline = Baseline(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            baseline_type="bom",
            root_item_id=item.id,
            root_version_id=resolved_version_id,
            root_config_id=item.config_id,
            snapshot=snapshot,
            max_levels=max_levels,
            effective_at=effective_at,
            include_substitutes=include_substitutes,
            include_effectivity=include_effectivity,
            line_key=line_key or "child_config",
            item_count=item_count,
            relationship_count=rel_count,
            created_by_id=created_by_id,
        )
        self.session.add(baseline)
        self.session.commit()
        return baseline

    def list_baselines(
        self,
        *,
        root_item_id: Optional[str],
        root_version_id: Optional[str],
        created_by_id: Optional[int],
        limit: int,
        offset: int,
    ) -> Tuple[List[Baseline], int]:
        q = self.session.query(Baseline)
        if root_item_id:
            q = q.filter(Baseline.root_item_id == root_item_id)
        if root_version_id:
            q = q.filter(Baseline.root_version_id == root_version_id)
        if created_by_id is not None:
            q = q.filter(Baseline.created_by_id == created_by_id)

        total = q.count()
        items = (
            q.order_by(Baseline.created_at.desc()).offset(offset).limit(limit).all()
        )
        return items, total

    def get_baseline(self, baseline_id: str) -> Optional[Baseline]:
        return self.session.get(Baseline, baseline_id)

    def compare_baseline(
        self,
        *,
        baseline: Baseline,
        target_type: str,
        target_id: str,
        max_levels: int,
        effective_at: Optional[datetime],
        include_substitutes: bool,
        include_effectivity: bool,
        include_child_fields: bool,
        include_relationship_props: Optional[List[str]],
        line_key: Optional[str],
    ) -> Dict[str, Any]:
        left_tree = baseline.snapshot
        if not isinstance(left_tree, dict):
            raise ValueError("Baseline snapshot missing")

        effective_at = self._normalize_effective_at(effective_at)

        target_tree: Dict[str, Any]
        if target_type == "baseline":
            target = self.get_baseline(target_id)
            if not target or not isinstance(target.snapshot, dict):
                raise ValueError("Target baseline not found")
            target_tree = target.snapshot
        elif target_type == "item":
            target_tree = self.bom_service.get_bom_structure(
                target_id,
                levels=max_levels,
                effective_date=effective_at,
                include_substitutes=include_substitutes,
            )
        elif target_type == "version":
            target_tree = self.bom_service.get_bom_for_version(
                target_id, levels=max_levels, include_substitutes=include_substitutes
            )
        else:
            raise ValueError("target_type must be item|version|baseline")

        compare_key = line_key or baseline.line_key or "child_config"
        return self.bom_service.compare_bom_trees(
            left_tree,
            target_tree,
            include_relationship_props=include_relationship_props,
            include_child_fields=include_child_fields,
            line_key=compare_key,
            include_substitutes=include_substitutes,
            include_effectivity=include_effectivity,
        )
