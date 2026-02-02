from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import csv
import io
import json
import uuid

from sqlalchemy.orm import Session

from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.baseline import (
    Baseline,
    BaselineComparison,
    BaselineMember,
    BaselineScope,
)
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

    def _add_item_member(
        self,
        baseline: Baseline,
        item: Item,
        *,
        level: int,
        path: str,
        quantity: Optional[str] = None,
        member_type: str = "item",
    ) -> BaselineMember:
        member = BaselineMember(
            id=str(uuid.uuid4()),
            baseline_id=baseline.id,
            item_id=item.id,
            item_number=item.config_id,
            item_revision=item.properties.get("revision") if item.properties else None,
            item_generation=item.generation,
            item_type=item.item_type_id,
            level=level,
            path=path,
            quantity=quantity,
            member_type=member_type,
            item_state=item.state,
        )
        self.session.add(member)
        return member

    def _add_relationship_member(
        self,
        baseline: Baseline,
        relationship_id: str,
        *,
        level: int,
        path: str,
    ) -> BaselineMember:
        member = BaselineMember(
            id=str(uuid.uuid4()),
            baseline_id=baseline.id,
            relationship_id=relationship_id,
            item_number=relationship_id,
            level=level,
            path=path,
            member_type="relationship",
        )
        self.session.add(member)
        return member

    def _add_bom_members(
        self,
        baseline: Baseline,
        bom: Dict[str, Any],
        *,
        level: int,
        path: str,
    ) -> None:
        children = bom.get("children") or []
        for child_entry in children:
            rel = child_entry.get("relationship") or {}
            child_data = child_entry.get("child") or {}
            child_id = child_data.get("id")

            if not child_id:
                continue

            child_item = self.session.get(Item, child_id)
            if not child_item:
                continue

            rel_props = rel.get("properties") or {}
            quantity = rel_props.get("quantity", rel_props.get("qty", 1))
            quantity = str(quantity)

            child_path = f"{path}/{child_item.config_id or child_id}"

            self._add_item_member(
                baseline,
                child_item,
                level=level,
                path=child_path,
                quantity=quantity,
            )

            if baseline.include_relationships and rel.get("id"):
                self._add_relationship_member(
                    baseline,
                    rel.get("id"),
                    level=level,
                    path=child_path,
                )

            if child_data.get("children"):
                self._add_bom_members(
                    baseline,
                    child_data,
                    level=level + 1,
                    path=child_path,
                )

    def _add_document_members(self, baseline: Baseline, item_id: str) -> None:
        from yuantus.meta_engine.models.file import FileContainer

        docs = (
            self.session.query(FileContainer)
            .filter(FileContainer.item_id == item_id)
            .all()
        )

        for doc in docs:
            member = BaselineMember(
                id=str(uuid.uuid4()),
                baseline_id=baseline.id,
                document_id=doc.id,
                item_number=doc.filename,
                item_revision=doc.document_version,
                item_type=doc.document_type,
                level=0,
                path="documents",
                member_type="document",
            )
            self.session.add(member)

    def _populate_members(self, baseline: Baseline, snapshot: Dict[str, Any]) -> None:
        if not baseline.root_item_id:
            return
        root_item = self.session.get(Item, baseline.root_item_id)
        if not root_item:
            return

        root_path = root_item.config_id or "root"
        self._add_item_member(baseline, root_item, level=0, path="")

        if baseline.include_bom:
            self._add_bom_members(
                baseline,
                snapshot,
                level=1,
                path=root_path,
            )

        if baseline.include_documents:
            self._add_document_members(baseline, baseline.root_item_id)

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
        baseline_type: Optional[str] = None,
        scope: Optional[str] = None,
        baseline_number: Optional[str] = None,
        effective_date: Optional[datetime] = None,
        include_bom: Optional[bool] = None,
        include_documents: Optional[bool] = None,
        include_relationships: Optional[bool] = None,
        bom_levels: Optional[int] = None,
        eco_id: Optional[str] = None,
        auto_populate: bool = True,
        state: Optional[str] = None,
    ) -> Baseline:
        item, resolved_version_id = self._resolve_root(root_item_id, root_version_id)
        self._ensure_can_read(item, str(created_by_id or "guest"), roles)

        baseline_type = baseline_type or "bom"
        scope = scope or BaselineScope.PRODUCT.value
        if baseline_number is None:
            baseline_number = f"BL-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        effective_at = self._normalize_effective_at(effective_date or effective_at)
        levels = bom_levels if bom_levels is not None else max_levels
        include_bom = True if include_bom is None else include_bom
        if include_documents is None:
            include_documents = baseline_type != "bom"
        if include_relationships is None:
            include_relationships = baseline_type != "bom"

        snapshot_levels = levels if include_bom else 0
        if resolved_version_id:
            snapshot = self.bom_service.get_bom_for_version(
                resolved_version_id, levels=snapshot_levels, include_substitutes=include_substitutes
            )
        else:
            snapshot = self.bom_service.get_bom_structure(
                item.id,
                levels=snapshot_levels,
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
            baseline_type=baseline_type,
            baseline_number=baseline_number,
            scope=scope,
            root_item_id=item.id,
            root_version_id=resolved_version_id,
            root_config_id=item.config_id,
            eco_id=eco_id,
            snapshot=snapshot,
            max_levels=levels,
            effective_at=effective_at,
            include_bom=include_bom,
            include_substitutes=include_substitutes,
            include_effectivity=include_effectivity,
            include_documents=include_documents,
            include_relationships=include_relationships,
            line_key=line_key or "child_config",
            item_count=item_count,
            relationship_count=rel_count,
            state=state or "draft",
            created_by_id=created_by_id,
        )
        self.session.add(baseline)
        self.session.flush()
        if auto_populate:
            self._populate_members(baseline, snapshot)
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

    def validate_baseline(self, baseline_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        baseline = self.session.get(Baseline, baseline_id)
        if not baseline:
            raise ValueError(f"Baseline not found: {baseline_id}")

        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        members = (
            self.session.query(BaselineMember)
            .filter(BaselineMember.baseline_id == baseline_id)
            .all()
        )

        for member in members:
            if member.member_type == "item":
                item = self.session.get(Item, member.item_id) if member.item_id else None
                if not item:
                    errors.append(
                        {
                            "type": "missing_item",
                            "member_id": member.id,
                            "item_id": member.item_id,
                            "message": f"Item not found: {member.item_number}",
                        }
                    )
                    continue

                if item.state not in ("released", "approved"):
                    warnings.append(
                        {
                            "type": "unreleased_item",
                            "member_id": member.id,
                            "item_id": member.item_id,
                            "item_state": item.state,
                            "message": f"Item {member.item_number} is not released (state: {item.state})",
                        }
                    )

                if member.item_generation is not None and item.generation != member.item_generation:
                    warnings.append(
                        {
                            "type": "version_mismatch",
                            "member_id": member.id,
                            "expected_generation": member.item_generation,
                            "current_generation": item.generation,
                            "message": f"Item {member.item_number} version changed",
                        }
                    )

            elif member.member_type == "document":
                from yuantus.meta_engine.models.file import FileContainer

                doc = (
                    self.session.get(FileContainer, member.document_id)
                    if member.document_id
                    else None
                )
                if not doc:
                    errors.append(
                        {
                            "type": "missing_document",
                            "member_id": member.id,
                            "document_id": member.document_id,
                            "message": f"Document not found: {member.item_number}",
                        }
                    )

        is_valid = len(errors) == 0
        baseline.is_validated = is_valid
        baseline.validation_errors = {"errors": errors, "warnings": warnings}
        baseline.validated_at = datetime.utcnow()
        baseline.validated_by_id = user_id
        self.session.add(baseline)
        self.session.commit()

        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "validated_at": baseline.validated_at.isoformat() if baseline.validated_at else None,
        }

    def compare_baselines(
        self,
        *,
        baseline_a_id: str,
        baseline_b_id: str,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        baseline_a = self.session.get(Baseline, baseline_a_id)
        baseline_b = self.session.get(Baseline, baseline_b_id)

        if not baseline_a or not baseline_b:
            raise ValueError("Baseline not found")

        members_a = (
            self.session.query(BaselineMember)
            .filter(BaselineMember.baseline_id == baseline_a_id)
            .all()
        )
        members_b = (
            self.session.query(BaselineMember)
            .filter(BaselineMember.baseline_id == baseline_b_id)
            .all()
        )

        def _key(member: BaselineMember) -> Tuple[str, Optional[str]]:
            if member.member_type == "document":
                return ("document", member.document_id or member.item_id)
            if member.member_type == "relationship":
                return ("relationship", member.relationship_id)
            return ("item", member.item_id)

        map_a = {_key(m): m for m in members_a}
        map_b = { _key(m): m for m in members_b }

        keys_a = set(map_a.keys())
        keys_b = set(map_b.keys())

        added: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        changed: List[Dict[str, Any]] = []
        unchanged: List[Dict[str, Any]] = []

        for key in keys_b - keys_a:
            m = map_b[key]
            added.append(
                {
                    "member_type": m.member_type,
                    "reference_id": m.item_id or m.document_id or m.relationship_id,
                    "item_number": m.item_number,
                    "revision": m.item_revision,
                }
            )

        for key in keys_a - keys_b:
            m = map_a[key]
            removed.append(
                {
                    "member_type": m.member_type,
                    "reference_id": m.item_id or m.document_id or m.relationship_id,
                    "item_number": m.item_number,
                    "revision": m.item_revision,
                }
            )

        for key in keys_a & keys_b:
            ma = map_a[key]
            mb = map_b[key]
            if ma.item_generation != mb.item_generation or ma.item_revision != mb.item_revision:
                changed.append(
                    {
                        "member_type": ma.member_type,
                        "reference_id": ma.item_id or ma.document_id or ma.relationship_id,
                        "item_number": ma.item_number,
                        "baseline_a": {
                            "revision": ma.item_revision,
                            "generation": ma.item_generation,
                        },
                        "baseline_b": {
                            "revision": mb.item_revision,
                            "generation": mb.item_generation,
                        },
                    }
                )
            else:
                unchanged.append(
                    {
                        "member_type": ma.member_type,
                        "reference_id": ma.item_id or ma.document_id or ma.relationship_id,
                        "item_number": ma.item_number,
                    }
                )

        comparison = BaselineComparison(
            id=str(uuid.uuid4()),
            baseline_a_id=baseline_a_id,
            baseline_b_id=baseline_b_id,
            added_count=len(added),
            removed_count=len(removed),
            changed_count=len(changed),
            unchanged_count=len(unchanged),
            differences={
                "added": added,
                "removed": removed,
                "changed": changed,
            },
            compared_by_id=user_id,
        )
        self.session.add(comparison)
        self.session.commit()

        return {
            "comparison_id": comparison.id,
            "baseline_a": {"id": baseline_a.id, "name": baseline_a.name},
            "baseline_b": {"id": baseline_b.id, "name": baseline_b.name},
            "summary": {
                "added": len(added),
                "removed": len(removed),
                "changed": len(changed),
                "unchanged": len(unchanged),
            },
            "details": {
                "added": added,
                "removed": removed,
                "changed": changed,
            },
        }

    def get_comparison_details(
        self,
        *,
        comparison_id: str,
        change_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Dict[str, Any]:
        comparison = self.session.get(BaselineComparison, comparison_id)
        if not comparison:
            raise ValueError("Baseline comparison not found")

        diff = comparison.differences or {}
        categories = {
            "added": diff.get("added") or [],
            "removed": diff.get("removed") or [],
            "changed": diff.get("changed") or [],
        }

        items: List[Dict[str, Any]] = []
        if change_type:
            if change_type not in categories:
                raise ValueError("Unsupported change_type")
            items = categories[change_type]
        else:
            for key in ("added", "removed", "changed"):
                items.extend(categories[key])

        total = len(items)
        sliced = items[offset : offset + limit]

        return {
            "comparison_id": comparison.id,
            "baseline_a_id": comparison.baseline_a_id,
            "baseline_b_id": comparison.baseline_b_id,
            "change_type": change_type,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": sliced,
        }

    def export_comparison_details(
        self,
        *,
        comparison_id: str,
        change_type: Optional[str],
        export_format: str,
        limit: int = 2000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        details = self.get_comparison_details(
            comparison_id=comparison_id,
            change_type=change_type,
            limit=limit,
            offset=offset,
        )

        normalized_format = export_format.lower().strip()
        if normalized_format not in {"csv", "json"}:
            raise ValueError("Unsupported export format")

        if normalized_format == "json":
            payload = json.dumps(details, ensure_ascii=False, default=str).encode("utf-8")
            return {"content": payload, "media_type": "application/json", "extension": "json"}

        items = details.get("items") or []
        columns: List[str] = []
        for item in items:
            for key in (item or {}).keys():
                if key not in columns:
                    columns.append(key)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for item in items:
            row = []
            for col in columns:
                value = (item or {}).get(col)
                if isinstance(value, (dict, list)):
                    row.append(json.dumps(value, ensure_ascii=False))
                elif value is None:
                    row.append("")
                else:
                    row.append(str(value))
            writer.writerow(row)
        content = buffer.getvalue().encode("utf-8-sig")
        return {"content": content, "media_type": "text/csv", "extension": "csv"}

    def release_baseline(
        self,
        baseline_id: str,
        user_id: Optional[int] = None,
        *,
        force: bool = False,
    ) -> Baseline:
        baseline = self.session.get(Baseline, baseline_id)
        if not baseline:
            raise ValueError(f"Baseline not found: {baseline_id}")

        if baseline.state == "released":
            raise ValueError("Baseline is already released")

        if not force and not baseline.is_validated:
            validation = self.validate_baseline(baseline_id, user_id)
            if not validation["is_valid"]:
                raise ValueError(f"Baseline validation failed: {validation['errors']}")

        baseline.state = "released"
        baseline.is_locked = True
        baseline.locked_at = datetime.utcnow()
        baseline.released_at = datetime.utcnow()
        baseline.released_by_id = user_id
        self.session.add(baseline)
        self.session.commit()
        return baseline

    def get_baseline_at_date(
        self,
        *,
        root_item_id: str,
        target_date: datetime,
        baseline_type: Optional[str] = None,
    ) -> Optional[Baseline]:
        query = self.session.query(Baseline).filter(
            Baseline.root_item_id == root_item_id,
            Baseline.state == "released",
            Baseline.effective_at <= target_date,
        )
        if baseline_type:
            query = query.filter(Baseline.baseline_type == baseline_type)
        return query.order_by(Baseline.effective_at.desc()).first()

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
