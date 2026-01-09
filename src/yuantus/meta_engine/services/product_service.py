from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.exceptions.handlers import PermissionError
from yuantus.meta_engine.models.file import FileContainer, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction
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
