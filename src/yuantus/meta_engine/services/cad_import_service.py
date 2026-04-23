from __future__ import annotations

import hashlib
import io
import mimetypes
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.exceptions.handlers import PLMException, QuotaExceededError
from yuantus.integrations.cad_connectors import (
    registry as cad_registry,
    resolve_cad_sync_key,
)
from yuantus.meta_engine.models.file import FileContainer, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem
from yuantus.meta_engine.services.cad_service import CadService
from yuantus.meta_engine.services.engine import AMLEngine
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.version.file_service import VersionFileError, VersionFileService
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.security.auth.quota_service import QuotaService


_FILENAME_REV_RE = re.compile(r"(?i)(?:rev|revision)[\\s_-]*([A-Za-z0-9]+)$")
_FILENAME_VER_RE = re.compile(r"(?i)v(\\d+(?:\\.\\d+)*)$")


class CadImportError(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class CadImportValidationError(CadImportError):
    pass


class CadImportConflictError(CadImportError):
    pass


class CadImportQuotaError(CadImportError):
    pass


class CadImportUpstreamError(CadImportError):
    pass


@dataclass
class CadImportRequest:
    filename: str
    content: bytes
    item_id: Optional[str]
    file_role: str
    author: Optional[str]
    source_system: Optional[str]
    source_version: Optional[str]
    document_version: Optional[str]
    cad_format: Optional[str]
    cad_connector_id: Optional[str]
    create_preview_job: bool
    create_geometry_job: Optional[bool]
    geometry_format: str
    create_extract_job: Optional[bool]
    create_bom_job: bool
    auto_create_part: bool
    create_dedup_job: bool
    dedup_mode: str
    dedup_index: bool
    create_ml_job: bool
    authorization: Optional[str]


@dataclass
class CadImportJobResult:
    id: str
    task_type: str
    status: str


@dataclass
class CadImportResult:
    file_container: FileContainer
    is_duplicate: bool
    item_id: Optional[str]
    attachment_id: Optional[str]
    jobs: List[CadImportJobResult] = field(default_factory=list)
    quota_warnings: List[str] = field(default_factory=list)


def _calculate_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _get_mime_type(filename: str) -> str:
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def _validate_upload(filename: str, file_size: int) -> None:
    settings = get_settings()
    max_bytes = settings.FILE_UPLOAD_MAX_BYTES
    if max_bytes and file_size > max_bytes:
        raise CadImportValidationError(
            413,
            {
                "code": "FILE_TOO_LARGE",
                "max_bytes": max_bytes,
                "file_size": file_size,
            },
        )

    allowed = {
        ext.strip().lower().lstrip(".")
        for ext in settings.FILE_ALLOWED_EXTENSIONS.split(",")
        if ext.strip()
    }
    if allowed:
        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in allowed:
            raise CadImportValidationError(
                415,
                {
                    "code": "FILE_TYPE_NOT_ALLOWED",
                    "extension": ext,
                },
            )


def _get_document_type(extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if ext in {"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}:
        return "2d"
    if ext in {
        "step",
        "stp",
        "iges",
        "igs",
        "stl",
        "obj",
        "gltf",
        "glb",
        "sldprt",
        "sldasm",
        "ipt",
        "iam",
        "prt",
        "asm",
        "catpart",
        "catproduct",
        "par",
        "psm",
        "3dm",
    }:
        return "3d"
    return "other"


def _json_text(expr):
    if hasattr(expr, "as_string"):
        return expr.as_string()
    if hasattr(expr, "astext"):
        return expr.astext
    return cast(expr, String)


def _normalize_text(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_filename_attrs(stem: str) -> Dict[str, str]:
    stem = stem.strip()
    if not stem:
        return {}

    attrs: Dict[str, str] = {}
    revision = None

    match = _FILENAME_REV_RE.search(stem)
    if match:
        revision = match.group(1)
        stem = stem[: match.start()].rstrip(" _-")
    else:
        match = _FILENAME_VER_RE.search(stem)
        if match:
            revision = f"v{match.group(1)}"
            stem = stem[: match.start()].rstrip(" _-")

    if revision:
        attrs["revision"] = revision

    if stem:
        attrs.setdefault("description", stem)

    return attrs


def _build_auto_part_properties(
    item_type: ItemType, attrs: Dict[str, Any], filename: Optional[str]
) -> tuple[str, Dict[str, Any]]:
    attributes = dict(attrs or {})
    lower_attributes = {str(k).lower(): v for k, v in attributes.items()}
    prop_defs = {prop.name: prop for prop in (item_type.properties or [])}

    def _get_value(*keys: str) -> Optional[Any]:
        for key in keys:
            if key in attributes:
                return attributes[key]
            lower = key.lower()
            if lower in lower_attributes:
                return lower_attributes[lower]
        return None

    def _apply_length_limit(name: str, value: Optional[Any]) -> Optional[Any]:
        if value is None:
            return None
        text = str(value)
        prop = prop_defs.get(name)
        max_len = getattr(prop, "length", None) if prop else None
        if isinstance(max_len, int) and max_len > 0 and len(text) > max_len:
            return text[:max_len]
        return value

    def _looks_like_uuid(value: Optional[str]) -> bool:
        if not value:
            return False
        text = value.strip()
        if len(text) < 24:
            return False
        hex_part = text.replace("-", "")
        if len(hex_part) < 24:
            return False
        if not all(c in "0123456789abcdefABCDEF" for c in hex_part):
            return False
        if text.count("-") >= 2:
            return True
        return len(hex_part) in (24, 32)

    item_number = _get_value(
        "part_number",
        "item_number",
        "item_no",
        "number",
        "drawing_no",
        "drawing_number",
    )
    if not item_number:
        stem = Path(filename).stem if filename else ""
        item_number = stem or f"PART-{uuid.uuid4().hex[:8]}"

    item_number = _normalize_text(item_number) or f"PART-{uuid.uuid4().hex[:8]}"
    stem = Path(filename).stem if filename else ""
    if stem and _looks_like_uuid(item_number):
        item_number = stem
    item_number = _apply_length_limit("item_number", item_number) or item_number
    prop_names = {prop.name for prop in (item_type.properties or [])}
    props: Dict[str, Any] = {}

    if "item_number" in prop_names:
        props["item_number"] = item_number

    description = _normalize_text(_get_value("description", "title", "name"))
    if description and "description" in prop_names:
        props["description"] = _apply_length_limit("description", description) or description

    if "name" in prop_names:
        props["name"] = _apply_length_limit("name", description or item_number) or (
            description or item_number
        )

    revision = _normalize_text(_get_value("revision", "rev"))
    if revision and "revision" in prop_names:
        props["revision"] = _apply_length_limit("revision", revision) or revision

    if filename:
        parsed = _parse_filename_attrs(Path(filename).stem)
        if "description" not in props and "description" in prop_names:
            parsed_desc = _normalize_text(parsed.get("description"))
            if parsed_desc:
                props["description"] = _apply_length_limit("description", parsed_desc) or parsed_desc
                if "name" in prop_names and not props.get("name"):
                    props["name"] = _apply_length_limit("name", parsed_desc) or parsed_desc
        if "revision" not in props and "revision" in prop_names:
            parsed_rev = _normalize_text(parsed.get("revision"))
            if parsed_rev:
                props["revision"] = _apply_length_limit("revision", parsed_rev) or parsed_rev

    for prop in item_type.properties or []:
        if prop.name in props or not prop.is_cad_synced:
            continue
        cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
        value = _get_value(cad_key)
        if value is not None:
            props[prop.name] = value

    return item_number, props


def _build_missing_updates(
    existing: Optional[Dict[str, Any]], incoming: Dict[str, Any]
) -> Dict[str, Any]:
    existing = existing or {}
    updates: Dict[str, Any] = {}

    for key, value in incoming.items():
        if value is None:
            continue
        current = existing.get(key)
        if current is None:
            updates[key] = value
            continue
        if isinstance(current, str) and not current.strip():
            updates[key] = value

    return updates


def _get_cad_format(extension: str) -> Optional[str]:
    ext = extension.lower().lstrip(".")
    cad_formats = {
        "step": "STEP",
        "stp": "STEP",
        "iges": "IGES",
        "igs": "IGES",
        "sldprt": "SOLIDWORKS",
        "sldasm": "SOLIDWORKS",
        "ipt": "INVENTOR",
        "iam": "INVENTOR",
        "prt": "NX",
        "asm": "NX",
        "catpart": "CATIA",
        "catproduct": "CATIA",
        "par": "SOLID_EDGE",
        "psm": "SOLID_EDGE",
        "3dm": "RHINO",
        "dwg": "AUTOCAD",
        "dxf": "AUTOCAD",
        "stl": "STL",
        "obj": "OBJ",
        "gltf": "GLTF",
        "glb": "GLTF",
        "pdf": "PDF",
    }
    return cad_formats.get(ext)


def _resolve_cad_metadata(
    extension: str,
    override_format: Optional[str],
    connector_id: Optional[str],
    *,
    content: Optional[bytes] = None,
    filename: Optional[str] = None,
    source_system: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    connector = None
    if connector_id:
        connector = cad_registry.find_by_id(connector_id)
    if not connector and override_format:
        connector = cad_registry.find_by_format(override_format)
    if not connector:
        connector = cad_registry.detect_by_content(
            content,
            filename=filename,
            source_system=source_system,
        )
    if not connector:
        connector = cad_registry.resolve(None, extension)

    if connector:
        return {
            "cad_format": connector.info.cad_format,
            "document_type": connector.info.document_type,
            "connector_id": connector.info.id,
        }

    resolved = cad_registry.resolve_metadata(override_format, extension)
    cad_format = resolved.cad_format or _get_cad_format(extension)
    document_type = resolved.document_type or _get_document_type(extension)
    return {
        "cad_format": cad_format,
        "document_type": document_type,
        "connector_id": resolved.connector_id,
    }


def _ensure_current_version_attachment_editable(
    db: Session,
    item: Optional[Item],
    *,
    file_id: str,
    file_role: str,
    user_id: int,
) -> None:
    if not item or not item.current_version_id:
        return

    version = db.get(ItemVersion, item.current_version_id)
    if not version:
        return

    if version.checked_out_by_id and version.checked_out_by_id != user_id:
        raise CadImportConflictError(
            409,
            f"Version {version.id} is checked out by another user",
        )

    vf_service = VersionFileService(db)
    try:
        vf_service.ensure_file_editable(
            version.id,
            file_id,
            user_id,
            file_role=file_role,
        )
    except VersionFileError as exc:
        detail = str(exc)
        lower = detail.lower()
        if "is not attached to version" in lower:
            return
        if (
            "checked out" in lower
            or "locked" in lower
            or "released" in lower
            or "specify file_role" in lower
        ):
            raise CadImportConflictError(409, detail) from exc
        raise CadImportValidationError(400, detail) from exc


def _ensure_duplicate_file_repair_editable(
    db: Session,
    file_container: Optional[FileContainer],
    *,
    user_id: int,
) -> None:
    if not file_container:
        return

    from yuantus.meta_engine.version.models import VersionFile

    assocs = (
        db.query(VersionFile, ItemVersion)
        .join(ItemVersion, VersionFile.version_id == ItemVersion.id)
        .filter(
            VersionFile.file_id == file_container.id,
            ItemVersion.is_current.is_(True),
        )
        .order_by(ItemVersion.id.asc(), VersionFile.file_role.asc())
        .all()
    )
    if not assocs:
        return

    vf_service = VersionFileService(db)
    for assoc, version in assocs:
        try:
            vf_service.ensure_file_editable(
                version.id,
                file_container.id,
                user_id,
                file_role=assoc.file_role,
            )
        except VersionFileError as exc:
            detail = str(exc)
            lower = detail.lower()
            if (
                "checked out" in lower
                or "locked" in lower
                or "released" in lower
                or "specify file_role" in lower
            ):
                raise CadImportConflictError(409, detail) from exc
            raise CadImportValidationError(400, detail) from exc


class CadImportService:
    def __init__(self, db: Session, identity_db: Session):
        self.db = db
        self.identity_db = identity_db

    def import_file(self, request: CadImportRequest, user: Any) -> CadImportResult:
        if not request.content:
            raise CadImportValidationError(400, "Empty file")
        _validate_upload(request.filename, len(request.content))

        quota_warnings: List[str] = []
        checksum = _calculate_checksum(request.content)
        existing = (
            self.db.query(FileContainer)
            .filter(FileContainer.checksum == checksum)
            .first()
        )
        is_duplicate = existing is not None

        file_container: FileContainer
        if existing:
            file_service = FileService()
            if existing.system_path and not file_service.file_exists(existing.system_path):
                _ensure_duplicate_file_repair_editable(
                    self.db,
                    existing,
                    user_id=user.id,
                )
                file_service.upload_file(io.BytesIO(request.content), existing.system_path)
                existing.file_size = len(request.content)
                existing.mime_type = _get_mime_type(request.filename)
                self.db.add(existing)
                self.db.commit()
            file_container = existing
        else:
            quota_service = QuotaService(self.identity_db, meta_db=self.db)
            decisions = quota_service.evaluate(
                user.tenant_id,
                deltas={"files": 1, "storage_bytes": len(request.content)},
            )
            if decisions:
                if quota_service.mode == "soft":
                    quota_warnings.append(QuotaService.build_warning(decisions))
                else:
                    detail = {
                        "code": "QUOTA_EXCEEDED",
                        **QuotaService.build_error_payload(user.tenant_id, decisions),
                    }
                    raise CadImportQuotaError(429, detail)

            file_id = str(uuid.uuid4())
            ext = Path(request.filename).suffix.lower()
            resolved = _resolve_cad_metadata(
                ext,
                request.cad_format,
                request.cad_connector_id,
                content=request.content,
                filename=request.filename,
                source_system=request.source_system,
            )
            final_format = resolved["cad_format"]
            document_type = resolved["document_type"]
            resolved_connector_id = resolved.get("connector_id")
            stored_filename = f"{file_id}{ext}"
            storage_key = f"{document_type}/{file_id[:2]}/{stored_filename}"

            file_service = FileService()
            file_service.upload_file(io.BytesIO(request.content), storage_key)

            file_container = FileContainer(
                id=file_id,
                filename=request.filename,
                file_type=ext.lstrip("."),
                mime_type=_get_mime_type(request.filename),
                file_size=len(request.content),
                checksum=checksum,
                system_path=storage_key,
                document_type=document_type,
                is_native_cad=final_format is not None,
                cad_format=final_format,
                cad_connector_id=resolved_connector_id,
                created_by_id=user.id,
                author=request.author,
                source_system=request.source_system,
                source_version=request.source_version,
                document_version=request.document_version,
            )
            self.db.add(file_container)
            self.db.commit()

        item_id = request.item_id
        if request.auto_create_part and not item_id:
            item_id = self._auto_create_or_update_part(
                file_container,
                request.filename,
                user,
            )

        if request.create_bom_job and not item_id:
            raise CadImportValidationError(
                400,
                "create_bom_job requires item_id or auto_create_part",
            )

        attachment_id = self._attach_to_item(
            item_id=item_id,
            file_container=file_container,
            file_role=request.file_role,
            user_id=user.id,
        )

        jobs = self._plan_and_enqueue_jobs(
            request=request,
            file_container=file_container,
            item_id=item_id,
            user=user,
            quota_warnings=quota_warnings,
        )

        return CadImportResult(
            file_container=file_container,
            is_duplicate=is_duplicate,
            item_id=item_id,
            attachment_id=attachment_id,
            jobs=jobs,
            quota_warnings=quota_warnings,
        )

    def _auto_create_or_update_part(
        self,
        file_container: FileContainer,
        filename: str,
        user: Any,
    ) -> str:
        part_type = self.db.get(ItemType, "Part")
        if not part_type:
            raise CadImportValidationError(404, "Part ItemType not found")

        cad_service = CadService(self.db)
        file_service = FileService()
        try:
            extracted_attrs, _source = cad_service.extract_attributes_for_file(
                file_container,
                file_service=file_service,
                return_source=True,
            )
        except JobFatalError as exc:
            raise CadImportUpstreamError(502, str(exc)) from exc
        except Exception as exc:
            raise CadImportValidationError(400, str(exc)) from exc

        item_number, part_props = _build_auto_part_properties(
            part_type,
            extracted_attrs,
            filename,
        )
        identity = str(user.id)
        roles = list(user.roles or [])
        if user.is_superuser and "superuser" not in roles:
            roles.append("superuser")
        engine = AMLEngine(self.db, identity_id=identity, roles=roles)
        existing_part = (
            self.db.query(Item)
            .filter(Item.item_type_id == "Part")
            .filter(_json_text(Item.properties["item_number"]) == item_number)
            .first()
        )
        if existing_part:
            item_id = existing_part.id
            updates = _build_missing_updates(existing_part.properties, part_props)
            if updates:
                aml_update = GenericItem(
                    id=item_id,
                    type="Part",
                    action=AMLAction.update,
                    properties=updates,
                )
                try:
                    engine.apply(aml_update)
                    self.db.commit()
                except PLMException as exc:
                    self.db.rollback()
                    raise CadImportError(exc.status_code, exc.to_dict()) from exc
                except Exception as exc:
                    self.db.rollback()
                    raise CadImportValidationError(400, str(exc)) from exc
            return item_id

        aml = GenericItem(type="Part", action=AMLAction.add, properties=part_props)
        try:
            result = engine.apply(aml)
            self.db.commit()
        except PLMException as exc:
            self.db.rollback()
            raise CadImportError(exc.status_code, exc.to_dict()) from exc
        except Exception as exc:
            self.db.rollback()
            raise CadImportValidationError(400, str(exc)) from exc
        item_id = result.get("id")
        if not item_id:
            raise CadImportUpstreamError(500, "Auto Part creation failed")
        return item_id

    def _attach_to_item(
        self,
        *,
        item_id: Optional[str],
        file_container: FileContainer,
        file_role: str,
        user_id: int,
    ) -> Optional[str]:
        if not item_id:
            return None

        item = self.db.get(Item, item_id)
        if not item:
            raise CadImportValidationError(404, "Item not found")

        existing_link = (
            self.db.query(ItemFile)
            .filter(ItemFile.item_id == item_id, ItemFile.file_id == file_container.id)
            .first()
        )
        if existing_link:
            _ensure_current_version_attachment_editable(
                self.db,
                item,
                file_id=existing_link.file_id,
                file_role=existing_link.file_role,
                user_id=user_id,
            )
            if existing_link.file_role != file_role:
                _ensure_current_version_attachment_editable(
                    self.db,
                    item,
                    file_id=existing_link.file_id,
                    file_role=file_role,
                    user_id=user_id,
                )
            existing_link.file_role = file_role
            self.db.add(existing_link)
            self.db.commit()
            return existing_link.id

        _ensure_current_version_attachment_editable(
            self.db,
            item,
            file_id=file_container.id,
            file_role=file_role,
            user_id=user_id,
        )
        link = ItemFile(
            item_id=item_id,
            file_id=file_container.id,
            file_role=file_role,
        )
        self.db.add(link)
        self.db.commit()
        return link.id

    def _plan_and_enqueue_jobs(
        self,
        *,
        request: CadImportRequest,
        file_container: FileContainer,
        item_id: Optional[str],
        user: Any,
        quota_warnings: List[str],
    ) -> List[CadImportJobResult]:
        geometry_enabled = request.create_geometry_job
        if geometry_enabled is None:
            geometry_enabled = False

        planned_jobs = 0
        if request.create_preview_job and file_container.is_cad_file():
            planned_jobs += 1
        if geometry_enabled and file_container.is_cad_file():
            planned_jobs += 1
        extract_enabled = request.create_extract_job
        if extract_enabled is None:
            extract_enabled = bool(file_container.is_cad_file())
        if extract_enabled and file_container.is_cad_file():
            planned_jobs += 1
        if request.create_bom_job and file_container.is_cad_file():
            planned_jobs += 1
        if request.create_dedup_job and file_container.file_type in {
            "dwg",
            "dxf",
            "pdf",
            "png",
            "jpg",
            "jpeg",
        }:
            planned_jobs += 1
        if request.create_ml_job and file_container.file_type in {
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "dwg",
            "dxf",
        }:
            planned_jobs += 1

        if planned_jobs:
            quota_service = QuotaService(self.identity_db, meta_db=self.db)
            decisions = quota_service.evaluate(
                user.tenant_id,
                deltas={"active_jobs": planned_jobs},
            )
            if decisions:
                if quota_service.mode == "soft":
                    quota_warnings.append(QuotaService.build_warning(decisions))
                else:
                    detail = {
                        "code": "QUOTA_EXCEEDED",
                        **QuotaService.build_error_payload(user.tenant_id, decisions),
                    }
                    raise CadImportQuotaError(429, detail)

        jobs: List[CadImportJobResult] = []
        job_service = JobService(self.db)
        user_roles = list(user.roles or [])

        def _enqueue(task_type: str, payload: Dict[str, Any], priority: int) -> None:
            if item_id:
                payload = {**payload, "item_id": item_id}
            payload = {
                **payload,
                "file_id": file_container.id,
                "source_path": file_container.system_path,
                "cad_connector_id": file_container.cad_connector_id,
                "cad_format": file_container.cad_format,
                "document_type": file_container.document_type,
                "tenant_id": user.tenant_id,
                "org_id": user.org_id,
                "user_id": user.id,
                "roles": user_roles,
                "authorization": request.authorization,
            }
            try:
                job = job_service.create_job(
                    task_type=task_type,
                    payload=payload,
                    user_id=user.id,
                    priority=priority,
                    dedupe=True,
                )
            except QuotaExceededError as exc:
                raise CadImportQuotaError(exc.status_code, exc.to_dict()) from exc
            jobs.append(
                CadImportJobResult(
                    id=job.id,
                    task_type=job.task_type,
                    status=job.status,
                )
            )

        if request.create_preview_job and file_container.is_cad_file():
            _enqueue("cad_preview", {"file_id": file_container.id}, priority=10)

        if geometry_enabled and file_container.is_cad_file():
            _enqueue(
                "cad_geometry",
                {"file_id": file_container.id, "target_format": request.geometry_format},
                priority=20,
            )

        if extract_enabled and file_container.is_cad_file():
            _enqueue("cad_extract", {"file_id": file_container.id}, priority=25)

        if request.create_bom_job and file_container.is_cad_file():
            _enqueue("cad_bom", {"file_id": file_container.id}, priority=27)

        if request.create_dedup_job and file_container.file_type in {
            "dwg",
            "dxf",
            "pdf",
            "png",
            "jpg",
            "jpeg",
        }:
            _enqueue(
                "cad_dedup_vision",
                {
                    "file_id": file_container.id,
                    "mode": request.dedup_mode,
                    "user_name": user.username,
                    "index": bool(request.dedup_index),
                },
                priority=30,
            )

        if request.create_ml_job and file_container.file_type in {
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "dwg",
            "dxf",
        }:
            _enqueue(
                "cad_ml_vision",
                {"file_id": file_container.id},
                priority=40,
            )

        return jobs
