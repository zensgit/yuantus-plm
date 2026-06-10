"""
Check-in/Check-out Service
Manages locking and versioning for concurrent editing.
Phase 6: Deep CAD Integration
"""

import uuid
import logging
from pathlib import Path
import io
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.service import VersionService, IterationService
from yuantus.exceptions.handlers import PermissionError, ValidationError
from yuantus.meta_engine.events.domain_events import FileCheckedInEvent
from yuantus.meta_engine.events.transactional import enqueue_event
from yuantus.meta_engine.models.file import (
    ConversionStatus,
    DocumentType,
    FileContainer,
    FileRole,
    ItemFile,
)
from yuantus.meta_engine.services.file_service import FileService

logger = logging.getLogger(__name__)


class CheckinService:
    def __init__(self, session: Session):
        self.session = session
        self.version_service = VersionService(session)
        self.iteration_service = IterationService(session)

    def check_out(self, item_id: str, user_id: int) -> Item:
        """Lock an item for editing."""
        item = self.session.get(Item, item_id)
        if not item:
            raise ValidationError(f"Item {item_id} not found")

        if item.locked_by_id:
            if item.locked_by_id == user_id:
                return item  # Already locked by this user
            raise ValidationError(f"Item is already locked by user {item.locked_by_id}")

        # Check permission (simple check, assume caller handled RBAC)
        # In a real scenario, we should call permission_service.check_permission(..., 'checkout')

        item.locked_by_id = user_id
        self.session.add(item)
        self.session.commit()
        return item


class _CheckinFileService:
    """
    Minimal file helper for CAD check-in.

    This is intentionally small; the main REST upload flow lives in `file_storage_router`.
    """

    def __init__(self, session: Session):
        self.session = session
        self.storage = FileService()

    def upload_file(self, content: bytes, filename: str) -> FileContainer:
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix.lower().lstrip(".")
        storage_key = f"cad/{file_id[:2]}/{file_id}.{ext or 'bin'}"
        stored_key = self.storage.upload_file(
            file_obj=io.BytesIO(content), file_path=storage_key
        )

        # WP1.3: derive document_type the same way the import path does (was a
        # hard-coded OTHER), so a checked-in 3D native gets document_type="3d" and
        # is selectable as model M for 2D/3D staleness. Lazy import to avoid a
        # cad_import_service -> engine -> checkin_service import cycle.
        from yuantus.meta_engine.services.cad_import_service import _resolve_cad_metadata

        resolved = _resolve_cad_metadata(ext, None, None, content=content, filename=filename)

        fc = FileContainer(
            id=file_id,
            filename=filename,
            file_type=ext or None,
            mime_type=None,
            file_size=len(content),
            checksum=None,
            system_path=stored_key,
            document_type=resolved["document_type"] or DocumentType.OTHER.value,
            is_native_cad=True,
            cad_format=resolved["cad_format"] or (ext.upper() if ext else None),
            cad_connector_id=resolved.get("connector_id"),
            conversion_status=ConversionStatus.PENDING.value,
        )
        self.session.add(fc)
        self.session.flush()
        return fc

    def get_file_path(self, file_id: str) -> str:
        fc = self.session.get(FileContainer, file_id)
        if not fc:
            return ""
        # Local storage provider can expose a local path; otherwise return system_path.
        local_path = self.storage.get_local_path(fc.system_path)
        return local_path or fc.system_path or ""


class CheckinManager:
    """
    CAD-facing check-in/check-out façade.

    The unit tests expect:
    - checkout() delegates to VersionService.checkout
    - checkin() delegates to VersionService.checkin and sets properties native_file/viewable_file
    """

    def __init__(self, session: Session, *, user_id: int):
        self.session = session
        self.user_id = int(user_id)
        self.version_service = VersionService(session)
        self.file_service = _CheckinFileService(session)

    def checkout(
        self,
        item_id: str,
        *,
        client_host: Optional[str] = None,
        client_workspace_path: Optional[str] = None,
        client_info: Optional[Dict[str, Any]] = None,
    ):
        return self.version_service.checkout(
            item_id,
            self.user_id,
            comment="CAD Checkout",
            client_host=client_host,
            client_workspace_path=client_workspace_path,
            client_info=client_info,
        )

    def undo_checkout(self, item_id: str):
        # No explicit undo in VersionService; use checkin to release the checkout lock.
        return self.version_service.checkin(
            item_id, self.user_id, properties=None, comment="CAD Undo Checkout"
        )

    def _upsert_native_role_row(
        self, item_id: str, file_id: str, import_batch_id: str
    ) -> None:
        """WP1.3: materialize the native model as a ``native_cad`` ItemFile (the
        current-state authority), so CadConsistencyService can select it as model M.
        Upsert by (item_id, file_id, native_cad) to respect the unique index."""
        role = FileRole.NATIVE_CAD.value
        existing = (
            self.session.query(ItemFile)
            .filter_by(item_id=item_id, file_id=file_id, file_role=role)
            .first()
        )
        if existing:
            existing.import_batch_id = import_batch_id
            self.session.add(existing)
        else:
            self.session.add(
                ItemFile(
                    item_id=item_id,
                    file_id=file_id,
                    file_role=role,
                    import_batch_id=import_batch_id,
                )
            )
        self.session.flush()

    def checkin(
        self,
        item_id: str,
        content: bytes,
        filename: str,
        import_batch_id: Optional[str] = None,
    ):
        from yuantus.meta_engine.services.job_service import JobService

        batch_id = import_batch_id or str(uuid.uuid4())
        native = self.file_service.upload_file(content, filename)
        props: Dict[str, Any] = {"native_file": native.id}

        item = self.session.get(Item, item_id)
        version_id = item.current_version_id if item else None

        # WP1.3: register the native as a native_cad ItemFile (carries import_batch_id).
        # VersionService.checkin's file sync mirrors it into the current VersionFile.
        if item is not None:
            self._upsert_native_role_row(item_id, native.id, batch_id)

        job_service = JobService(self.session)
        ext = Path(filename).suffix.lower().lstrip(".")
        payload: Dict[str, Any] = {
            "file_id": native.id,
            "item_id": item_id,
            "version_id": version_id,
            "filename": filename,
            "cad_format": ext.upper() if ext else None,
        }
        preview_job = job_service.create_job(
            "cad_preview",
            dict(payload),
            user_id=self.user_id,
            max_attempts=3,
            dedupe=True,
        )
        geometry_job = job_service.create_job(
            "cad_geometry",
            dict(payload, target_format="glTF"),
            user_id=self.user_id,
            max_attempts=3,
            dedupe=True,
        )
        props["cad_conversion_job_ids"] = [preview_job.id, geometry_job.id]
        logger.info(
            "CAD checkin queued jobs item_id=%s file_id=%s preview_job=%s geometry_job=%s",
            item_id,
            native.id,
            preview_job.id,
            geometry_job.id,
        )

        result = self.version_service.checkin(
            item_id, self.user_id, properties=props, comment="CAD Checkin"
        )

        # WP1.3: refresh 2D/3D staleness for this part (non-fatal -- advisory).
        try:
            from yuantus.meta_engine.services.cad_consistency_service import (
                CadConsistencyService,
            )

            CadConsistencyService(self.session).recompute(item_id)
        except Exception:  # noqa: BLE001 - advisory recompute, never blocks checkin
            logger.warning(
                "WP1.3 staleness recompute failed for item %s", item_id, exc_info=True
            )

        return result

    def undo_check_out(self, item_id: str, user_id: int) -> Item:
        """Unlock an item without saving changes."""
        item = self.session.get(Item, item_id)
        if not item:
            raise ValidationError(f"Item {item_id} not found")

        if not item.locked_by_id:
            raise ValidationError("Item is not locked")

        # Allow admin/superuser to unlock? For now strict check.
        if item.locked_by_id != user_id:
            raise PermissionError("Cannot undo check-out locked by another user")

        item.locked_by_id = None
        self.session.add(item)
        self.session.commit()
        return item

    def check_in(
        self,
        item_id: str,
        user_id: int,
        new_properties: Dict[str, Any] = None,
        new_file_info: Dict[str, Any] = None,
    ) -> Item:
        """
        Unlock an item, update properties, and create a new version snapshot.
        """
        item = self.session.get(Item, item_id)
        if not item:
            raise ValidationError(f"Item {item_id} not found")

        if item.locked_by_id != user_id:
            raise PermissionError(
                "Cannot check-in item locked by another user (or not locked)"
            )

        # 1. Update properties on the CURRENT item (Master)
        if new_properties:
            current_props = dict(item.properties or {})
            current_props.update(new_properties)
            item.properties = current_props

        # 2. Handle File (if Item represents a file)
        if new_file_info:
            current_props = dict(item.properties or {})
            current_props.update(new_file_info)
            item.properties = current_props

        # Unlock
        item.locked_by_id = None
        self.session.add(item)
        self.session.flush()

        # 3. Create Version Snapshot (History)
        # This snapshots the CURRENT state of the item (after update)
        if item.is_versionable and item.current_version_id:
            self.iteration_service.create_iteration(
                version_id=item.current_version_id,
                user_id=user_id,
                description=f"Check-in by user {user_id}",
                properties=item.properties,
            )  # Closing parenthesis added here

        enqueue_event(
            self.session,
            FileCheckedInEvent(
                item_id=item.id,
                file_id=item.properties.get(
                    "file_id"
                ),  # Assuming item properties store file_id
                new_version_id=item.current_version_id,
                actor_id=user_id,
            )
        )
        self.session.commit()
        return item
