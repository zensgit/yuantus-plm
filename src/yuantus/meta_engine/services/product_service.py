from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.eco import ECO, ECOState
from yuantus.meta_engine.models.file import FileContainer, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.eco_service import ECOApprovalService
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.meta_engine.version.models import ItemVersion


class ProductDetailService:
    def __init__(
        self,
        session: Session,
        user_id: Optional[str],
        roles: Optional[List[str]],
    ) -> None:
        self.session = session
        self.user_id = user_id or "guest"
        self.roles = roles or []
        self.permission_service = MetaPermissionService(session)

    def get_detail(
        self,
        item_id: str,
        *,
        include_versions: bool = True,
        include_files: bool = True,
        include_version_files: bool = False,
        include_bom_summary: bool = False,
        bom_summary_depth: int = 1,
        bom_effective_at: Optional[str] = None,
        include_where_used_summary: bool = False,
        where_used_recursive: bool = False,
        where_used_max_levels: int = 5,
        include_document_summary: bool = False,
        include_eco_summary: bool = False,
    ) -> Dict[str, Any]:
        item = self.session.get(Item, item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        if not self.permission_service.check_permission(
            item.item_type_id,
            AMLAction.get,
            user_id=str(self.user_id),
            user_roles=self.roles,
            item_state=item.state,
            item_owner_id=str(item.owner_id or item.created_by_id)
            if (item.owner_id or item.created_by_id)
            else None,
        ):
            raise PermissionError(action=AMLAction.get.value, resource=item.item_type_id)

        payload: Dict[str, Any] = {"item": self._serialize_item(item)}

        current_version = None
        if item.current_version_id:
            current_version = self.session.get(ItemVersion, item.current_version_id)
        if current_version:
            payload["current_version"] = self._serialize_version(current_version)

        if include_versions:
            payload["versions"] = self._get_versions(item.id)

        if include_files:
            payload["files"] = self._get_files(item.id)

        if include_version_files and current_version:
            payload["version_files"] = self._get_version_files(current_version)

        if include_bom_summary or include_where_used_summary:
            bom_allowed = self.permission_service.check_permission(
                "Part BOM",
                AMLAction.get,
                user_id=str(self.user_id),
                user_roles=self.roles,
            )
            if include_bom_summary:
                if bom_allowed:
                    payload["bom_summary"] = self._get_bom_summary(
                        item.id,
                        depth=bom_summary_depth,
                        effective_at=bom_effective_at,
                    )
                else:
                    payload["bom_summary"] = {"authorized": False}
            if include_where_used_summary:
                if bom_allowed:
                    payload["where_used_summary"] = self._get_where_used_summary(
                        item.id,
                        recursive=where_used_recursive,
                        max_levels=where_used_max_levels,
                    )
                else:
                    payload["where_used_summary"] = {"authorized": False}

        if include_document_summary:
            doc_allowed = self.permission_service.check_permission(
                "Document",
                AMLAction.get,
                user_id=str(self.user_id),
                user_roles=self.roles,
            )
            if doc_allowed:
                payload["document_summary"] = self._get_document_summary(item.id)
            else:
                payload["document_summary"] = {"authorized": False}

        if include_eco_summary:
            eco_allowed = self.permission_service.check_permission(
                "ECO",
                AMLAction.get,
                user_id=str(self.user_id),
                user_roles=self.roles,
            )
            if eco_allowed:
                payload["eco_summary"] = self._get_eco_summary(item.id)
            else:
                payload["eco_summary"] = {"authorized": False}

        return payload

    def _serialize_item(self, item: Item) -> Dict[str, Any]:
        props = item.properties or {}
        item_number = props.get("item_number") or props.get("number")
        return {
            "id": item.id,
            "type": item.item_type_id,
            "item_number": item_number,
            "number": item_number,
            "name": props.get("name"),
            "revision": props.get("revision"),
            "state": item.state,
            "config_id": item.config_id,
            "generation": item.generation,
            "is_current": item.is_current,
            "current_version_id": item.current_version_id,
            "properties": props,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
            "created_by_id": item.created_by_id,
            "modified_by_id": item.modified_by_id,
            "owner_id": item.owner_id,
        }

    def _serialize_version(self, version: ItemVersion) -> Dict[str, Any]:
        return {
            "id": version.id,
            "item_id": version.item_id,
            "generation": version.generation,
            "revision": version.revision,
            "version_label": version.version_label,
            "state": version.state,
            "is_current": version.is_current,
            "is_released": version.is_released,
            "branch_name": version.branch_name,
            "checked_out_by_id": version.checked_out_by_id,
            "checked_out_at": (
                version.checked_out_at.isoformat() if version.checked_out_at else None
            ),
            "released_at": (
                version.released_at.isoformat() if version.released_at else None
            ),
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }

    def _get_versions(self, item_id: str) -> List[Dict[str, Any]]:
        versions = (
            self.session.query(ItemVersion)
            .filter(ItemVersion.item_id == item_id)
            .order_by(ItemVersion.generation, ItemVersion.revision)
            .all()
        )
        return [self._serialize_version(v) for v in versions]

    def _get_files(self, item_id: str) -> List[Dict[str, Any]]:
        item_files = (
            self.session.query(ItemFile)
            .filter(ItemFile.item_id == item_id)
            .order_by(ItemFile.sequence.asc())
            .all()
        )

        files: List[Dict[str, Any]] = []
        for item_file in item_files:
            file_container: Optional[FileContainer] = item_file.file
            if not file_container:
                continue
            files.append(
                {
                    "attachment_id": item_file.id,
                    "file_id": file_container.id,
                    "filename": file_container.filename,
                    "file_role": item_file.file_role,
                    "description": item_file.description,
                    "file_type": file_container.file_type,
                    "mime_type": file_container.mime_type,
                    "file_size": file_container.file_size,
                    "document_type": file_container.document_type,
                    "preview_url": (
                        f"/api/v1/file/{file_container.id}/preview"
                        if file_container.preview_path
                        else None
                    ),
                    "geometry_url": (
                        f"/api/v1/file/{file_container.id}/geometry"
                        if file_container.geometry_path
                        else None
                    ),
                    "download_url": f"/api/v1/file/{file_container.id}/download",
                    "created_at": (
                        file_container.created_at.isoformat()
                        if file_container.created_at
                        else None
                    ),
                }
            )

        return files

    def _get_version_files(self, version: ItemVersion) -> List[Dict[str, Any]]:
        files: List[Dict[str, Any]] = []
        for vf in version.version_files or []:
            file_container = vf.file
            files.append(
                {
                    "id": vf.id,
                    "file_id": vf.file_id,
                    "file_role": vf.file_role,
                    "sequence": vf.sequence,
                    "is_primary": vf.is_primary,
                    "snapshot_path": vf.snapshot_path,
                    "filename": file_container.filename if file_container else None,
                    "file_type": file_container.file_type if file_container else None,
                    "file_size": file_container.file_size if file_container else None,
                }
            )
        return files

    def _get_bom_summary(
        self,
        item_id: str,
        *,
        depth: int,
        effective_at: Optional[str],
    ) -> Dict[str, Any]:
        service = BOMService(self.session)
        effective_date = None
        if effective_at:
            try:
                from datetime import datetime

                effective_date = datetime.fromisoformat(effective_at)
            except ValueError:
                effective_date = None

        tree = service.get_bom_structure(
            item_id,
            levels=max(depth, 0),
            effective_date=effective_date,
        )

        direct_children = len(tree.get("children") or [])
        total_children = 0
        max_depth = 0

        def walk(node: Dict[str, Any], level: int) -> None:
            nonlocal total_children, max_depth
            max_depth = max(max_depth, level)
            for child_entry in node.get("children") or []:
                total_children += 1
                child = child_entry.get("child") or {}
                walk(child, level + 1)

        walk(tree, 0)
        return {
            "authorized": True,
            "depth": depth,
            "direct_children": direct_children,
            "total_children": total_children,
            "max_depth": max_depth,
        }

    def _get_where_used_summary(
        self,
        item_id: str,
        *,
        recursive: bool,
        max_levels: int,
    ) -> Dict[str, Any]:
        service = BOMService(self.session)
        parents = service.get_where_used(
            item_id=item_id,
            recursive=recursive,
            max_levels=max_levels,
        )
        sample: List[Dict[str, Any]] = []
        for entry in parents[:5]:
            parent = entry.get("parent") or {}
            props = parent.get("properties") or {}
            item_number = parent.get("item_number") or props.get("item_number") or props.get(
                "number"
            )
            sample.append(
                {
                    "id": parent.get("id"),
                    "item_number": item_number,
                    "name": parent.get("name") or props.get("name"),
                    "level": entry.get("level"),
                }
            )

        return {
            "authorized": True,
            "count": len(parents),
            "recursive": recursive,
            "max_levels": max_levels,
            "sample": sample,
        }

    def _get_document_summary(self, item_id: str) -> Dict[str, Any]:
        rel_types = (
            self.session.query(ItemType.id)
            .filter(ItemType.is_relationship.is_(True))
            .filter(
                or_(
                    ItemType.id.ilike("%document%part%"),
                    ItemType.id.ilike("%part%document%"),
                )
            )
            .all()
        )
        rel_type_ids = [row[0] for row in rel_types]
        if not rel_type_ids:
            return {"authorized": True, "count": 0, "state_counts": {}, "sample": []}

        relations = (
            self.session.query(Item)
            .filter(
                Item.item_type_id.in_(rel_type_ids),
                Item.is_current.is_(True),
                or_(Item.source_id == item_id, Item.related_id == item_id),
            )
            .all()
        )

        doc_ids = set()
        for rel in relations:
            if rel.source_id == item_id and rel.related_id:
                doc_ids.add(rel.related_id)
            elif rel.related_id == item_id and rel.source_id:
                doc_ids.add(rel.source_id)

        if not doc_ids:
            return {"authorized": True, "count": 0, "state_counts": {}, "sample": []}

        docs = (
            self.session.query(Item)
            .filter(Item.id.in_(list(doc_ids)))
            .order_by(Item.updated_at.desc(), Item.created_at.desc())
            .all()
        )
        state_counts: Dict[str, int] = {}
        sample: List[Dict[str, Any]] = []
        for doc in docs:
            state_counts[doc.state] = state_counts.get(doc.state, 0) + 1
            if len(sample) < 5:
                props = doc.properties or {}
                item_number = props.get("item_number") or props.get("number")
                sample.append(
                    {
                        "id": doc.id,
                        "item_number": item_number,
                        "name": props.get("name"),
                        "state": doc.state,
                        "current_version_id": doc.current_version_id,
                    }
                )

        return {
            "authorized": True,
            "count": len(docs),
            "state_counts": state_counts,
            "sample": sample,
        }

    def _get_eco_summary(self, item_id: str) -> Dict[str, Any]:
        ecos = (
            self.session.query(ECO)
            .filter(ECO.product_id == item_id)
            .order_by(ECO.updated_at.desc(), ECO.created_at.desc())
            .all()
        )
        state_counts: Dict[str, int] = {}
        for eco in ecos:
            state_counts[eco.state] = state_counts.get(eco.state, 0) + 1

        last_applied = None
        for eco in ecos:
            if eco.state == ECOState.DONE.value:
                last_applied = {
                    "eco_id": eco.id,
                    "name": eco.name,
                    "product_version_after": eco.product_version_after,
                    "updated_at": eco.updated_at.isoformat() if eco.updated_at else None,
                }
                break

        pending_items: List[Dict[str, Any]] = []
        try:
            approval_service = ECOApprovalService(self.session)
            user_id_int = int(self.user_id)
            pending = approval_service.get_pending_approvals(user_id_int)
            eco_ids = {eco.id for eco in ecos}
            pending_items = [p for p in pending if p.get("eco_id") in eco_ids][:5]
        except (ValueError, TypeError):
            pending_items = []

        return {
            "authorized": True,
            "count": len(ecos),
            "state_counts": state_counts,
            "pending_approvals": {
                "count": len(pending_items),
                "items": pending_items,
            },
            "last_applied": last_applied,
        }
