from __future__ import annotations

import csv
import json
import io
import os
import re
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Response
from pydantic import BaseModel, Field
from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.config import get_settings
from yuantus.integrations.cad_connectors import (
    registry as cad_registry,
    reload_connectors,
    resolve_cad_sync_key,
)

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.exceptions.handlers import PLMException, QuotaExceededError
from yuantus.meta_engine.models.file import FileContainer, FileRole, ItemFile
from yuantus.meta_engine.models.meta_schema import ItemType, Property
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem
from yuantus.meta_engine.services.cad_service import CadService
from yuantus.meta_engine.services.engine import AMLEngine
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.job_errors import JobFatalError
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.services.checkin_service import CheckinManager
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.quota_service import QuotaService

router = APIRouter(prefix="/cad", tags=["CAD"])

"""
CAD Connector API
Handles Document Locking and Versioning.
"""

_FILENAME_REV_RE = re.compile(r"(?i)(?:rev|revision)[\\s_-]*([A-Za-z0-9]+)$")
_FILENAME_VER_RE = re.compile(r"(?i)v(\\d+(?:\\.\\d+)*)$")


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    roles = set(user.roles or [])
    if "admin" not in roles and "superuser" not in roles:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def get_checkin_manager(
    user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> CheckinManager:
    # RBACUser should have an integer ID map?
    # user.id is the key (99, 1, 2)
    return CheckinManager(db, user_id=user.id)


class CadImportJob(BaseModel):
    id: str
    task_type: str
    status: str


class CadImportResponse(BaseModel):
    file_id: str
    filename: str
    checksum: str
    is_duplicate: bool
    item_id: Optional[str] = None
    attachment_id: Optional[str] = None
    jobs: List[CadImportJob] = Field(default_factory=list)
    download_url: str
    preview_url: Optional[str] = None
    geometry_url: Optional[str] = None
    cad_manifest_url: Optional[str] = None
    cad_document_url: Optional[str] = None
    cad_metadata_url: Optional[str] = None
    cad_format: Optional[str] = None
    cad_connector_id: Optional[str] = None
    document_type: Optional[str] = None
    is_native_cad: bool = False
    author: Optional[str] = None
    source_system: Optional[str] = None
    source_version: Optional[str] = None
    document_version: Optional[str] = None


class CadConnectorInfoResponse(BaseModel):
    id: str
    label: str
    cad_format: str
    document_type: str
    extensions: List[str]
    aliases: List[str] = Field(default_factory=list)
    priority: int
    description: Optional[str] = None


class CadConnectorReloadRequest(BaseModel):
    config_path: Optional[str] = None
    config: Optional[Any] = None


class CadConnectorReloadResponse(BaseModel):
    config_path: Optional[str] = None
    custom_loaded: int
    errors: List[str] = Field(default_factory=list)


class CadSyncTemplateRow(BaseModel):
    property_name: str
    label: Optional[str] = None
    data_type: Optional[str] = None
    is_cad_synced: bool = False
    cad_key: Optional[str] = None


class CadSyncTemplateResponse(BaseModel):
    item_type_id: str
    properties: List[CadSyncTemplateRow]


class CadSyncTemplateApplyResponse(BaseModel):
    item_type_id: str
    updated: int
    skipped: int
    missing: List[str] = Field(default_factory=list)


class CadExtractAttributesResponse(BaseModel):
    file_id: str
    cad_format: Optional[str] = None
    cad_connector_id: Optional[str] = None
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    extracted_at: Optional[str] = None
    extracted_attributes: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


def _calculate_checksum(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()


def _get_mime_type(filename: str) -> str:
    import mimetypes

    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def _validate_upload(filename: str, file_size: int) -> None:
    settings = get_settings()
    max_bytes = settings.FILE_UPLOAD_MAX_BYTES
    if max_bytes and file_size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail={
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
            raise HTTPException(
                status_code=415,
                detail={
                    "code": "FILE_TYPE_NOT_ALLOWED",
                    "extension": ext,
                },
            )


def _get_document_type(extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if ext in {"dwg", "dxf", "pdf"}:
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

    def _get_value(*keys: str) -> Optional[Any]:
        for key in keys:
            if key in attributes:
                return attributes[key]
            lower = key.lower()
            if lower in lower_attributes:
                return lower_attributes[lower]
        return None

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
    prop_names = {prop.name for prop in (item_type.properties or [])}
    props: Dict[str, Any] = {}

    if "item_number" in prop_names:
        props["item_number"] = item_number

    description = _normalize_text(_get_value("description", "title", "name"))
    if description and "description" in prop_names:
        props["description"] = description

    if "name" in prop_names:
        props["name"] = description or item_number

    revision = _normalize_text(_get_value("revision", "rev"))
    if revision and "revision" in prop_names:
        props["revision"] = revision

    if filename:
        parsed = _parse_filename_attrs(Path(filename).stem)
        if "description" not in props and "description" in prop_names:
            parsed_desc = _normalize_text(parsed.get("description"))
            if parsed_desc:
                props["description"] = parsed_desc
                if "name" in prop_names and not props.get("name"):
                    props["name"] = parsed_desc
        if "revision" not in props and "revision" in prop_names:
            parsed_rev = _normalize_text(parsed.get("revision"))
            if parsed_rev:
                props["revision"] = parsed_rev

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


@router.get("/connectors", response_model=List[CadConnectorInfoResponse])
def list_cad_connectors() -> List[CadConnectorInfoResponse]:
    connectors = sorted(cad_registry.list(), key=lambda info: info.id)
    return [
        CadConnectorInfoResponse(
            id=info.id,
            label=info.label,
            cad_format=info.cad_format,
            document_type=info.document_type,
            extensions=list(info.extensions),
            aliases=list(info.aliases),
            priority=info.priority,
            description=info.description,
        )
        for info in connectors
    ]


@router.post("/connectors/reload", response_model=CadConnectorReloadResponse)
def reload_cad_connectors(
    req: CadConnectorReloadRequest,
    _: CurrentUser = Depends(require_admin),
) -> CadConnectorReloadResponse:
    settings = get_settings()
    config_path = req.config_path
    if config_path and not settings.CAD_CONNECTORS_ALLOW_PATH_OVERRIDE:
        raise HTTPException(
            status_code=403,
            detail="Path override disabled (set CAD_CONNECTORS_ALLOW_PATH_OVERRIDE=true)",
        )
    if req.config is not None:
        result = reload_connectors(config_payload=req.config)
    else:
        result = reload_connectors(config_path=config_path)
    return CadConnectorReloadResponse(
        config_path=config_path or settings.CAD_CONNECTORS_CONFIG_PATH or None,
        custom_loaded=len(result.entries),
        errors=result.errors,
    )


def _csv_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


@router.get("/sync-template/{item_type_id}", response_model=CadSyncTemplateResponse)
def get_cad_sync_template(
    item_type_id: str,
    output_format: str = "csv",
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    rows: List[CadSyncTemplateRow] = []
    for prop in item_type.properties or []:
        cad_key = None
        if prop.is_cad_synced:
            cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
        rows.append(
            CadSyncTemplateRow(
                property_name=prop.name,
                label=prop.label,
                data_type=prop.data_type,
                is_cad_synced=bool(prop.is_cad_synced),
                cad_key=cad_key,
            )
        )

    if output_format.lower() == "json":
        return CadSyncTemplateResponse(item_type_id=item_type_id, properties=rows)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["property_name", "label", "data_type", "is_cad_synced", "cad_key"])
    for row in rows:
        writer.writerow(
            [
                row.property_name,
                row.label or "",
                row.data_type or "",
                "true" if row.is_cad_synced else "false",
                row.cad_key or "",
            ]
        )
    output.seek(0)
    filename = f"cad_sync_template_{item_type_id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)


@router.post("/sync-template/{item_type_id}", response_model=CadSyncTemplateApplyResponse)
async def apply_cad_sync_template(
    item_type_id: str,
    file: UploadFile = File(...),
    _: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> CadSyncTemplateApplyResponse:
    item_type = db.query(ItemType).filter(ItemType.id == item_type_id).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Empty template file")

    text = payload.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    props_by_name = {prop.name: prop for prop in (item_type.properties or [])}

    updated = 0
    skipped = 0
    missing: List[str] = []

    for row in reader:
        name = (row.get("property_name") or row.get("name") or "").strip()
        if not name:
            skipped += 1
            continue
        prop = props_by_name.get(name)
        if not prop:
            missing.append(name)
            continue

        cad_key = (row.get("cad_key") or row.get("cad_attribute") or "").strip()
        sync_flag = _csv_bool(row.get("is_cad_synced"))
        changed = False

        if sync_flag is not None and prop.is_cad_synced != sync_flag:
            prop.is_cad_synced = sync_flag
            changed = True

        if cad_key or sync_flag:
            ui_opts = prop.ui_options
            if isinstance(ui_opts, str):
                try:
                    ui_opts = json.loads(ui_opts)
                except Exception:
                    ui_opts = {}
            if not isinstance(ui_opts, dict):
                ui_opts = {}
            if cad_key:
                ui_opts["cad_key"] = cad_key
            else:
                ui_opts.pop("cad_key", None)
            prop.ui_options = ui_opts
            changed = True

        if changed:
            db.add(prop)
            updated += 1
        else:
            skipped += 1

    if updated:
        item_type.properties_schema = None
        db.add(item_type)
    db.commit()

    return CadSyncTemplateApplyResponse(
        item_type_id=item_type_id,
        updated=updated,
        skipped=skipped,
        missing=missing,
    )


@router.get("/files/{file_id}/attributes", response_model=CadExtractAttributesResponse)
def get_cad_attributes(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadExtractAttributesResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if file_container.cad_attributes is not None:
        extracted_at = file_container.cad_attributes_updated_at
        return CadExtractAttributesResponse(
            file_id=file_container.id,
            cad_format=file_container.cad_format,
            cad_connector_id=file_container.cad_connector_id,
            job_id=None,
            job_status="completed",
            extracted_at=extracted_at.isoformat() if extracted_at else None,
            extracted_attributes=file_container.cad_attributes or {},
            source=file_container.cad_attributes_source,
        )

    jobs = (
        db.query(ConversionJob)
        .filter(ConversionJob.task_type == "cad_extract")
        .order_by(ConversionJob.created_at.desc())
        .limit(50)
        .all()
    )
    matched_job = None
    for job in jobs:
        payload = job.payload or {}
        if str(payload.get("file_id") or "") == file_id:
            matched_job = job
            break

    if not matched_job:
        raise HTTPException(status_code=404, detail="No cad_extract data found")

    payload = matched_job.payload or {}
    result = payload.get("result") or {}
    extracted_attributes = result.get("extracted_attributes") or {}
    extracted_at = matched_job.completed_at or matched_job.created_at

    return CadExtractAttributesResponse(
        file_id=file_container.id,
        cad_format=file_container.cad_format,
        cad_connector_id=file_container.cad_connector_id,
        job_id=matched_job.id,
        job_status=matched_job.status,
        extracted_at=extracted_at.isoformat() if extracted_at else None,
        extracted_attributes=extracted_attributes,
        source=result.get("source"),
    )


@router.post("/import", response_model=CadImportResponse)
async def import_cad(
    response: Response,
    file: UploadFile = File(...),
    item_id: Optional[str] = Form(default=None, description="Attach to an existing item id"),
    file_role: str = Form(default=FileRole.NATIVE_CAD.value, description="Attachment role"),
    author: Optional[str] = Form(default=None, description="File author"),
    source_system: Optional[str] = Form(default=None, description="Source system name"),
    source_version: Optional[str] = Form(default=None, description="Source system version"),
    document_version: Optional[str] = Form(default=None, description="Document version label"),
    cad_format: Optional[str] = Form(
        default=None,
        description="Override CAD format/vendor label (e.g., GSTARCAD, ZWCAD, HAOCHEN, ZHONGWANG)",
    ),
    cad_connector_id: Optional[str] = Form(
        default=None,
        description="Explicit connector id override (e.g., gstarcad, zwcad)",
    ),
    create_preview_job: bool = Form(default=True),
    create_geometry_job: bool = Form(default=False),
    geometry_format: str = Form(default="gltf", description="obj|gltf|glb|stl"),
    create_extract_job: Optional[bool] = Form(
        default=None,
        description="Extract CAD attributes for sync (default: true when item_id is set)",
    ),
    auto_create_part: bool = Form(
        default=False,
        description="Auto-create Part when item_id is not provided",
    ),
    create_dedup_job: bool = Form(default=True),
    dedup_mode: str = Form(default="balanced", description="fast|balanced|precise"),
    create_ml_job: bool = Form(default=False, description="Call cad-ml-platform vision analyze"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
) -> CadImportResponse:
    """
    Import a CAD file: upload to storage, optionally attach to an item, then enqueue pipeline jobs.

    Jobs are created in `meta_conversion_jobs` and executed by `yuantus worker`.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    _validate_upload(file.filename, len(content))

    checksum = _calculate_checksum(content)
    existing = db.query(FileContainer).filter(FileContainer.checksum == checksum).first()
    is_duplicate = existing is not None

    def _append_quota_warning(message: str) -> None:
        if not message:
            return
        current = response.headers.get("X-Quota-Warning")
        response.headers["X-Quota-Warning"] = f"{current}; {message}" if current else message

    file_container: FileContainer
    if existing:
        file_service = FileService()
        if existing.system_path and not file_service.file_exists(existing.system_path):
            # Repair missing storage object for deduped uploads.
            file_service.upload_file(io.BytesIO(content), existing.system_path)
            existing.file_size = len(content)
            existing.mime_type = _get_mime_type(file.filename)
            db.add(existing)
            db.commit()
        file_container = existing
    else:
        quota_service = QuotaService(identity_db, meta_db=db)
        decisions = quota_service.evaluate(
            user.tenant_id, deltas={"files": 1, "storage_bytes": len(content)}
        )
        if decisions:
            if quota_service.mode == "soft":
                _append_quota_warning(QuotaService.build_warning(decisions))
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(user.tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        resolved = _resolve_cad_metadata(
            ext,
            cad_format,
            cad_connector_id,
            content=content,
            filename=file.filename,
            source_system=source_system,
        )
        final_format = resolved["cad_format"]
        document_type = resolved["document_type"]
        resolved_connector_id = resolved.get("connector_id")
        stored_filename = f"{file_id}{ext}"
        storage_key = f"{document_type}/{file_id[:2]}/{stored_filename}"

        file_service = FileService()
        file_service.upload_file(io.BytesIO(content), storage_key)

        file_container = FileContainer(
            id=file_id,
            filename=file.filename,
            file_type=ext.lstrip("."),
            mime_type=_get_mime_type(file.filename),
            file_size=len(content),
            checksum=checksum,
            system_path=storage_key,
            document_type=document_type,
            is_native_cad=final_format is not None,
            cad_format=final_format,
            cad_connector_id=resolved_connector_id,
            created_by_id=user.id,
            author=author,
            source_system=source_system,
            source_version=source_version,
            document_version=document_version,
        )
        db.add(file_container)
        db.commit()

    if auto_create_part and not item_id:
        part_type = db.get(ItemType, "Part")
        if not part_type:
            raise HTTPException(status_code=404, detail="Part ItemType not found")

        cad_service = CadService(db)
        file_service = FileService()
        try:
            extracted_attrs, _source = cad_service.extract_attributes_for_file(
                file_container,
                file_service=file_service,
                return_source=True,
            )
        except JobFatalError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        item_number, part_props = _build_auto_part_properties(
            part_type, extracted_attrs, file_container.filename
        )
        identity = str(user.id)
        roles = list(user.roles or [])
        if user.is_superuser and "superuser" not in roles:
            roles.append("superuser")
        engine = AMLEngine(db, identity_id=identity, roles=roles)
        existing_part = (
            db.query(Item)
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
                    db.commit()
                except PLMException as exc:
                    db.rollback()
                    raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
                except Exception as exc:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=str(exc))
        else:
            aml = GenericItem(type="Part", action=AMLAction.add, properties=part_props)
            try:
                result = engine.apply(aml)
                db.commit()
            except PLMException as exc:
                db.rollback()
                raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
            except Exception as exc:
                db.rollback()
                raise HTTPException(status_code=400, detail=str(exc))
            item_id = result.get("id")
            if not item_id:
                raise HTTPException(status_code=500, detail="Auto Part creation failed")

    attachment_id: Optional[str] = None
    if item_id:
        item = db.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.current_version_id:
            from yuantus.meta_engine.version.models import ItemVersion

            ver = db.get(ItemVersion, item.current_version_id)
            if ver and ver.checked_out_by_id and ver.checked_out_by_id != user.id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Version {ver.id} is checked out by another user",
                )

        existing_link = (
            db.query(ItemFile)
            .filter(ItemFile.item_id == item_id, ItemFile.file_id == file_container.id)
            .first()
        )
        if existing_link:
            existing_link.file_role = file_role
            db.add(existing_link)
            db.commit()
            attachment_id = existing_link.id
        else:
            link = ItemFile(
                item_id=item_id,
                file_id=file_container.id,
                file_role=file_role,
            )
            db.add(link)
            db.commit()
            attachment_id = link.id

    planned_jobs = 0
    if create_preview_job and file_container.is_cad_file():
        planned_jobs += 1
    if create_geometry_job and file_container.is_cad_file():
        planned_jobs += 1
    extract_enabled = create_extract_job
    if extract_enabled is None:
        extract_enabled = bool(item_id)
    if extract_enabled and file_container.is_cad_file():
        planned_jobs += 1
    if create_dedup_job and file_container.file_type in {"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}:
        planned_jobs += 1
    if create_ml_job and file_container.file_type in {"pdf", "png", "jpg", "jpeg", "dwg", "dxf"}:
        planned_jobs += 1

    if planned_jobs:
        quota_service = QuotaService(identity_db, meta_db=db)
        decisions = quota_service.evaluate(
            user.tenant_id, deltas={"active_jobs": planned_jobs}
        )
        if decisions:
            if quota_service.mode == "soft":
                _append_quota_warning(QuotaService.build_warning(decisions))
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(user.tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

    jobs: List[CadImportJob] = []
    job_service = JobService(db)

    def _enqueue(task_type: str, payload: Dict[str, Any], priority: int) -> None:
        if item_id:
            payload = {**payload, "item_id": item_id}
        payload = {
            **payload,
            "tenant_id": user.tenant_id,
            "org_id": user.org_id,
            "user_id": user.id,
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
            raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc
        jobs.append(CadImportJob(id=job.id, task_type=job.task_type, status=job.status))

    # Pipeline: preview -> geometry -> dedup -> ml
    if create_preview_job and file_container.is_cad_file():
        _enqueue("cad_preview", {"file_id": file_container.id}, priority=10)

    if create_geometry_job and file_container.is_cad_file():
        _enqueue(
            "cad_geometry",
            {"file_id": file_container.id, "target_format": geometry_format},
            priority=20,
        )

    if extract_enabled and file_container.is_cad_file():
        _enqueue("cad_extract", {"file_id": file_container.id}, priority=25)

    # Dedup is most relevant for 2D drawings; keep it optional.
    if create_dedup_job and file_container.file_type in {"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}:
        _enqueue(
            "cad_dedup_vision",
            {"file_id": file_container.id, "mode": dedup_mode, "user_name": user.username},
            priority=30,
        )

    if create_ml_job and file_container.file_type in {"pdf", "png", "jpg", "jpeg", "dwg", "dxf"}:
        _enqueue(
            "cad_ml_vision",
            {"file_id": file_container.id},
            priority=40,
        )

    preview_url = f"/api/v1/file/{file_container.id}/preview" if file_container.preview_path else None
    geometry_url = f"/api/v1/file/{file_container.id}/geometry" if file_container.geometry_path else None
    cad_manifest_url = (
        f"/api/v1/file/{file_container.id}/cad_manifest"
        if file_container.cad_manifest_path
        else None
    )
    cad_document_url = (
        f"/api/v1/file/{file_container.id}/cad_document"
        if file_container.cad_document_path
        else None
    )
    cad_metadata_url = (
        f"/api/v1/file/{file_container.id}/cad_metadata"
        if file_container.cad_metadata_path
        else None
    )
    return CadImportResponse(
        file_id=file_container.id,
        filename=file_container.filename,
        checksum=file_container.checksum,
        is_duplicate=is_duplicate,
        item_id=item_id,
        attachment_id=attachment_id,
        jobs=jobs,
        download_url=f"/api/v1/file/{file_container.id}/download",
        preview_url=preview_url,
        geometry_url=geometry_url,
        cad_manifest_url=cad_manifest_url,
        cad_document_url=cad_document_url,
        cad_metadata_url=cad_metadata_url,
        cad_format=file_container.cad_format,
        cad_connector_id=file_container.cad_connector_id,
        document_type=file_container.document_type,
        is_native_cad=file_container.is_native_cad,
        author=file_container.author,
        source_system=file_container.source_system,
        source_version=file_container.source_version,
        document_version=file_container.document_version,
    )


@router.post("/{item_id}/checkout")
def checkout_document(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    """
    Lock a document for editing.
    """
    try:
        item = mgr.checkout(item_id)
        # Commit handled by service or need manual commit?
        # Service flushes, but typically Router/Dependencies commit.
        # But CheckinManager commits/flushes?
        # CheckinManager.checkout does 'add' and 'flush'.
        # We need final commit.
        mgr.session.commit()
        return {
            "status": "success",
            "message": "Item locked.",
            "locked_by_id": item.locked_by_id,
        }
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        mgr.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{item_id}/undo-checkout")
def undo_checkout(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    try:
        mgr.undo_checkout(item_id)
        mgr.session.commit()
        return {"status": "success", "message": "Item unlocked."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/checkin")
def checkin_document(
    item_id: str,
    response: Response,
    file: UploadFile = File(...),
    mgr: CheckinManager = Depends(get_checkin_manager),
    user: CurrentUser = Depends(get_current_user),
    identity_db: Session = Depends(get_identity_db),
) -> Any:
    """
    Upload new file version and unlock.
    """
    try:
        content = file.file.read()
        filename = file.filename

        quota_service = QuotaService(identity_db, meta_db=mgr.session)
        decisions = quota_service.evaluate(
            user.tenant_id, deltas={"files": 1, "storage_bytes": len(content)}
        )
        if decisions:
            if quota_service.mode == "soft":
                response.headers["X-Quota-Warning"] = QuotaService.build_warning(decisions)
            else:
                detail = {
                    "code": "QUOTA_EXCEEDED",
                    **QuotaService.build_error_payload(user.tenant_id, decisions),
                }
                raise HTTPException(status_code=429, detail=detail)

        new_item = mgr.checkin(item_id, content, filename)
        mgr.session.commit()

        return {
            "status": "success",
            "new_item_id": new_item.id,
            "generation": new_item.generation,
        }
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        mgr.session.rollback()
        raise
    except Exception as e:
        mgr.session.rollback()
        # Log error
        raise HTTPException(status_code=500, detail=str(e))
