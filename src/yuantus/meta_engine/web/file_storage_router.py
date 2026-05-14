"""
File storage router.

This module owns upload, download, and preview endpoints split out of the
legacy file router.
"""

from __future__ import annotations

import base64
import hashlib
import io
import mimetypes
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.database import get_db
from yuantus.meta_engine.models.file import ConversionStatus, DocumentType, FileContainer
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.version.file_service import VersionFileError, VersionFileService
from yuantus.meta_engine.web.file_conversion_router import _queue_file_conversion_job
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.quota_service import QuotaService


file_storage_router = APIRouter(prefix="/file", tags=["File Management"])


class FileUploadResponse(BaseModel):
    """Response for file upload."""

    id: str
    filename: str
    url: str
    size: int
    mime_type: Optional[str] = None
    is_cad: bool = False
    preview_url: Optional[str] = None
    file_status_url: Optional[str] = None
    conversion_job_ids: List[str] = Field(default_factory=list)
    cad_manifest_url: Optional[str] = None
    cad_document_url: Optional[str] = None
    cad_metadata_url: Optional[str] = None
    cad_bom_url: Optional[str] = None
    cad_dedup_url: Optional[str] = None
    cad_document_schema_version: Optional[int] = None
    document_type: Optional[str] = None
    author: Optional[str] = None
    source_system: Optional[str] = None
    source_version: Optional[str] = None
    document_version: Optional[str] = None


def _calculate_checksum(file_content: bytes) -> str:
    """Calculate SHA256 checksum."""
    return hashlib.sha256(file_content).hexdigest()


def _get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def _ensure_duplicate_file_repair_editable(
    db: Session,
    file_container: Optional[FileContainer],
    *,
    user_id: Optional[int],
) -> None:
    if not file_container:
        return

    from yuantus.meta_engine.version.models import ItemVersion, VersionFile

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
        if user_id is None:
            if version.is_released:
                raise HTTPException(
                    status_code=409,
                    detail=f"Version {version.id} is released and locked",
                )
            if version.checked_out_by_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Version {version.id} is checked out by another user",
                )
            if assoc.checked_out_by_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"File {file_container.id} is checked out by another user",
                )
            continue

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
                raise HTTPException(status_code=409, detail=detail)
            raise HTTPException(status_code=400, detail=detail)


def _get_document_type(extension: str) -> str:
    """Determine document type from file extension."""
    ext = extension.lower().lstrip(".")

    if ext in {
        "step",
        "stp",
        "iges",
        "igs",
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
        "stl",
        "obj",
        "gltf",
        "glb",
        "3ds",
        "jt",
        "x_t",
        "x_b",
    }:
        return DocumentType.CAD_3D.value

    if ext in {"dwg", "dxf"}:
        return DocumentType.CAD_2D.value

    if ext in {"pdf", "pptx", "ppt"}:
        return DocumentType.PRESENTATION.value

    return DocumentType.OTHER.value


def _get_cad_format(extension: str) -> Optional[str]:
    """Get CAD format name from extension."""
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
    }
    return cad_formats.get(extension.lower().lstrip("."))


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


@file_storage_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    response: Response,
    file: UploadFile = File(...),
    generate_preview: bool = Query(
        True, description="Auto-generate preview for CAD files"
    ),
    user_id: Optional[int] = Depends(get_current_user_id_optional),
    author: Optional[str] = Form(default=None),
    source_system: Optional[str] = Form(default=None),
    source_version: Optional[str] = Form(default=None),
    document_version: Optional[str] = Form(default=None),
    db: Session = Depends(get_db),
    identity_db: Session = Depends(get_identity_db),
):
    """
    Upload a file to the vault.

    Creates a FileContainer record and optionally triggers CAD preview generation.
    """
    try:
        content = await file.read()
        file_size = len(content)
        _validate_upload(file.filename, file_size)

        checksum = _calculate_checksum(content)

        existing = (
            db.query(FileContainer).filter(FileContainer.checksum == checksum).first()
        )
        if existing:
            file_service = FileService()
            if existing.system_path and not file_service.file_exists(existing.system_path):
                _ensure_duplicate_file_repair_editable(
                    db,
                    existing,
                    user_id=user_id,
                )
                file_service.upload_file(io.BytesIO(content), existing.system_path)
                existing.file_size = file_size
                existing.mime_type = _get_mime_type(file.filename)
                db.add(existing)
                db.commit()
            return FileUploadResponse(
                id=existing.id,
                filename=existing.filename,
                url=f"/api/v1/file/{existing.id}/download",
                size=existing.file_size,
                mime_type=existing.mime_type,
                is_cad=existing.is_cad_file(),
                preview_url=(
                    f"/api/v1/file/{existing.id}/preview"
                    if existing.preview_path
                    else None
                ),
                file_status_url=(
                    f"/api/v1/file/{existing.id}/conversion_summary"
                    if existing.is_cad_file()
                    else None
                ),
                cad_bom_url=(
                    f"/api/v1/file/{existing.id}/cad_bom"
                    if existing.cad_bom_path
                    else None
                ),
                cad_dedup_url=(
                    f"/api/v1/file/{existing.id}/cad_dedup"
                    if existing.cad_dedup_path
                    else None
                ),
                cad_document_schema_version=existing.cad_document_schema_version,
                document_type=existing.document_type,
                author=existing.author,
                source_system=existing.source_system,
                source_version=existing.source_version,
                document_version=existing.document_version,
            )

        tenant_id = get_request_context().tenant_id
        if tenant_id:
            quota_service = QuotaService(identity_db, meta_db=db)
            decisions = quota_service.evaluate(
                tenant_id, deltas={"files": 1, "storage_bytes": file_size}
            )
            if decisions:
                if quota_service.mode == "soft":
                    response.headers["X-Quota-Warning"] = QuotaService.build_warning(decisions)
                else:
                    detail = {
                        "code": "QUOTA_EXCEEDED",
                        **QuotaService.build_error_payload(tenant_id, decisions),
                    }
                    raise HTTPException(status_code=429, detail=detail)

        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        stored_filename = f"{file_id}{ext}"

        type_dir = _get_document_type(ext)
        storage_key = f"{type_dir}/{file_id[:2]}/{stored_filename}"

        file_service = FileService()
        file_service.upload_file(io.BytesIO(content), storage_key)

        file_container = FileContainer(
            id=file_id,
            filename=file.filename,
            file_type=ext.lstrip("."),
            mime_type=_get_mime_type(file.filename),
            file_size=file_size,
            checksum=checksum,
            system_path=storage_key,
            document_type=_get_document_type(ext),
            is_native_cad=_get_cad_format(ext) is not None,
            cad_format=_get_cad_format(ext),
            conversion_status=(
                ConversionStatus.PENDING.value if _get_cad_format(ext) else None
            ),
            author=author,
            source_system=source_system,
            source_version=source_version,
            document_version=document_version,
        )
        db.add(file_container)

        preview_url = None
        conversion_job_ids: List[str] = []
        if generate_preview and file_container.is_cad_file():
            try:
                job = _queue_file_conversion_job(
                    db,
                    file_container,
                    "png",
                    priority=50,
                )
                conversion_job_ids = [job.id]
            except Exception as e:
                print(f"Preview generation failed: {e}")

        db.commit()

        return FileUploadResponse(
            id=file_id,
            filename=file.filename,
            url=f"/api/v1/file/{file_id}/download",
            size=file_size,
            mime_type=file_container.mime_type,
            is_cad=file_container.is_cad_file(),
            preview_url=preview_url,
            file_status_url=(
                f"/api/v1/file/{file_id}/conversion_summary"
                if file_container.is_cad_file()
                else None
            ),
            conversion_job_ids=conversion_job_ids,
            cad_bom_url=(
                f"/api/v1/file/{file_id}/cad_bom" if file_container.cad_bom_path else None
            ),
            cad_dedup_url=(
                f"/api/v1/file/{file_id}/cad_dedup" if file_container.cad_dedup_path else None
            ),
            cad_document_schema_version=file_container.cad_document_schema_version,
            document_type=file_container.document_type,
            author=file_container.author,
            source_system=file_container.source_system,
            source_version=file_container.source_version,
            document_version=file_container.document_version,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@file_storage_router.get("/{file_id}/download")
async def download_file(file_id: str, db: Session = Depends(get_db)):
    """Download the original file."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    file_service = FileService()

    local_path = file_service.get_local_path(file_container.system_path)
    if local_path and os.path.exists(local_path):
        return FileResponse(
            path=local_path,
            filename=file_container.filename,
            media_type=file_container.mime_type,
        )

    try:
        url = file_service.get_presigned_url(file_container.system_path)
        return RedirectResponse(url=url)
    except NotImplementedError:
        try:
            output_stream = io.BytesIO()
            file_service.download_file(file_container.system_path, output_stream)
            output_stream.seek(0)
            return StreamingResponse(
                output_stream,
                media_type=file_container.mime_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{file_container.filename}"'
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Download failed: {str(e)}"
            ) from e


@file_storage_router.get("/{file_id}/preview")
async def get_preview(file_id: str, db: Session = Depends(get_db)):
    """Get preview image for a file."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if file_container.preview_data:
        preview_bytes = base64.b64decode(file_container.preview_data)
        return Response(content=preview_bytes, media_type="image/png")

    if file_container.preview_path:
        file_service = FileService()

        local_path = file_service.get_local_path(file_container.preview_path)
        if local_path and os.path.exists(local_path):
            return FileResponse(path=local_path, media_type="image/png")

        try:
            url = file_service.get_presigned_url(file_container.preview_path)
            return RedirectResponse(url=url, status_code=302)
        except NotImplementedError:
            pass

        try:
            output_stream = io.BytesIO()
            file_service.download_file(file_container.preview_path, output_stream)
            output_stream.seek(0)
            return StreamingResponse(
                output_stream,
                media_type="image/png",
            )
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="Preview not available")
