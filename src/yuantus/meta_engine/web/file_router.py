"""
File Management API Router
Enhanced with FileContainer model and CAD conversion integration.

Based on patterns from:
- DocDoku-PLM: Vault path pattern, generated files subfolder
- Odoo PLM: Preview on save, conversion job queue
"""

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Query,
    Response,
    Form,
    Request,
)
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import uuid
import hashlib
import mimetypes
from pathlib import Path
import io
from urllib.parse import quote

from yuantus.database import get_db
from yuantus.config import get_settings
from yuantus.context import get_request_context
from yuantus.meta_engine.models.file import (
    FileContainer,
    ItemFile,
    FileRole,
    DocumentType,
    ConversionStatus,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.version.file_service import VersionFileService, VersionFileError
from yuantus.meta_engine.web.file_conversion_router import _queue_file_conversion_job
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.quota_service import QuotaService

file_router = APIRouter(prefix="/file", tags=["File Management"])

# Vault base path should align with FileService local storage base path in dev.
VAULT_DIR = get_settings().LOCAL_STORAGE_PATH


# ============================================================================
# Pydantic Models
# ============================================================================


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


class FileMetadata(BaseModel):
    """File metadata response."""

    id: str
    filename: str
    file_type: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    document_type: Optional[str] = None
    is_native_cad: bool = False
    cad_format: Optional[str] = None
    cad_connector_id: Optional[str] = None
    author: Optional[str] = None
    source_system: Optional[str] = None
    source_version: Optional[str] = None
    document_version: Optional[str] = None
    preview_url: Optional[str] = None
    geometry_url: Optional[str] = None
    cad_manifest_url: Optional[str] = None
    cad_document_url: Optional[str] = None
    cad_metadata_url: Optional[str] = None
    cad_bom_url: Optional[str] = None
    cad_dedup_url: Optional[str] = None
    cad_viewer_url: Optional[str] = None
    cad_document_schema_version: Optional[int] = None
    cad_review_state: Optional[str] = None
    cad_review_note: Optional[str] = None
    cad_review_by_id: Optional[int] = None
    cad_reviewed_at: Optional[str] = None
    conversion_status: Optional[str] = None
    viewer_readiness: Optional[dict] = None
    created_at: Optional[str] = None


class AttachFileRequest(BaseModel):
    """Request to attach file to item."""

    item_id: str
    file_id: str
    file_role: str = FileRole.ATTACHMENT.value
    description: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================


def _ensure_vault_dir():
    """Ensure vault directory exists."""
    os.makedirs(VAULT_DIR, exist_ok=True)


def _calculate_checksum(file_content: bytes) -> str:
    """Calculate SHA256 checksum."""
    return hashlib.sha256(file_content).hexdigest()


def _get_mime_type(filename: str) -> str:
    """Get MIME type from filename."""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


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

    from yuantus.meta_engine.version.models import ItemVersion

    version = db.get(ItemVersion, item.current_version_id)
    if not version:
        return

    if version.checked_out_by_id and version.checked_out_by_id != user_id:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version.id} is checked out by another user",
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
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


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


def _build_cad_viewer_url(request: Request, file_id: str, cad_manifest_path: Optional[str]) -> Optional[str]:
    if not cad_manifest_path:
        return None
    settings = get_settings()
    base_url = (
        settings.CADGF_ROUTER_PUBLIC_BASE_URL
        or settings.CADGF_ROUTER_BASE_URL
        or ""
    ).strip()
    if not base_url:
        return None
    manifest_url = f"{request.url_for('get_cad_manifest', file_id=file_id)}?rewrite=1"
    manifest_param = quote(str(manifest_url), safe="")
    return f"{base_url.rstrip('/')}/tools/web_viewer/index.html?manifest={manifest_param}"


def _get_document_type(extension: str) -> str:
    """Determine document type from file extension."""
    ext = extension.lower().lstrip(".")

    # 3D CAD formats
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

    # 2D CAD formats
    if ext in {"dwg", "dxf"}:
        return DocumentType.CAD_2D.value

    # Presentation/printout formats
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


# ============================================================================
# File Upload Endpoints
# ============================================================================


@file_router.post("/upload", response_model=FileUploadResponse)
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

    Returns:
        FileUploadResponse with file ID and URLs
    """
    # _ensure_vault_dir() # Handled by FileService

    try:
        # Read file content
        content = await file.read()
        file_size = len(content)
        _validate_upload(file.filename, file_size)

        # Calculate checksum
        checksum = _calculate_checksum(content)

        # Check for duplicate by checksum
        existing = (
            db.query(FileContainer).filter(FileContainer.checksum == checksum).first()
        )
        if existing:
            file_service = FileService()
            if existing.system_path and not file_service.file_exists(existing.system_path):
                # Repair missing storage object for deduped uploads.
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

        # Generate file ID and storage path
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        stored_filename = f"{file_id}{ext}"

        # Create directory structure: vault/{type}/{id[:2]}/{stored_filename}
        type_dir = _get_document_type(ext)
        storage_key = f"{type_dir}/{file_id[:2]}/{stored_filename}"

        # Upload using FileService
        file_service = FileService()
        file_service.upload_file(io.BytesIO(content), storage_key)

        # Create FileContainer record
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

        # Generate preview for CAD files (Async)
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
        raise HTTPException(status_code=500, detail=str(e))

@file_router.get("/{file_id}", response_model=FileMetadata)
async def get_file_metadata(file_id: str, request: Request, db: Session = Depends(get_db)):
    """Get file metadata by ID."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    return FileMetadata(
        id=file_container.id,
        filename=file_container.filename,
        file_type=file_container.file_type,
        mime_type=file_container.mime_type,
        file_size=file_container.file_size,
        checksum=file_container.checksum,
        document_type=file_container.document_type,
        is_native_cad=file_container.is_native_cad,
        cad_format=file_container.cad_format,
        cad_connector_id=file_container.cad_connector_id,
        author=file_container.author,
        source_system=file_container.source_system,
        source_version=file_container.source_version,
        document_version=file_container.document_version,
        preview_url=(
            f"/api/v1/file/{file_id}/preview" if file_container.preview_path else None
        ),
        geometry_url=(
            f"/api/v1/file/{file_id}/geometry" if file_container.geometry_path else None
        ),
        cad_manifest_url=(
            f"/api/v1/file/{file_id}/cad_manifest"
            if file_container.cad_manifest_path
            else None
        ),
        cad_document_url=(
            f"/api/v1/file/{file_id}/cad_document"
            if file_container.cad_document_path
            else None
        ),
        cad_metadata_url=(
            f"/api/v1/file/{file_id}/cad_metadata"
            if file_container.cad_metadata_path
            else None
        ),
        cad_bom_url=(
            f"/api/v1/file/{file_id}/cad_bom"
            if file_container.cad_bom_path
            else None
        ),
        cad_dedup_url=(
            f"/api/v1/file/{file_id}/cad_dedup"
            if file_container.cad_dedup_path
            else None
        ),
        cad_viewer_url=_build_cad_viewer_url(
            request,
            file_id,
            file_container.cad_manifest_path,
        ),
        cad_document_schema_version=file_container.cad_document_schema_version,
        cad_review_state=file_container.cad_review_state,
        cad_review_note=file_container.cad_review_note,
        cad_review_by_id=file_container.cad_review_by_id,
        cad_reviewed_at=(
            file_container.cad_reviewed_at.isoformat()
            if file_container.cad_reviewed_at
            else None
        ),
        conversion_status=file_container.conversion_status,
        viewer_readiness=CADConverterService(
            db, vault_base_path=VAULT_DIR
        ).assess_viewer_readiness(file_container),
        created_at=(
            file_container.created_at.isoformat() if file_container.created_at else None
        ),
    )


@file_router.get("/{file_id}/download")
async def download_file(file_id: str, db: Session = Depends(get_db)):
    """Download the original file."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    file_service = FileService()

    # Try local path first (for performance if on same server)
    local_path = file_service.get_local_path(file_container.system_path)
    if local_path and os.path.exists(local_path):
        return FileResponse(
            path=local_path,
            filename=file_container.filename,
            media_type=file_container.mime_type,
        )

    # Try presigned URL (S3) or fallback
    try:
        url = file_service.get_presigned_url(file_container.system_path)
        return RedirectResponse(url=url)
    except NotImplementedError:
        # Fallback: Stream content (not memory efficient for large files but works)
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
            raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@file_router.get("/{file_id}/preview")
async def get_preview(file_id: str, db: Session = Depends(get_db)):
    """Get preview image for a file."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    # If preview_data exists (base64), return it
    if file_container.preview_data:
        import base64

        preview_bytes = base64.b64decode(file_container.preview_data)
        return Response(content=preview_bytes, media_type="image/png")

    # If preview_path exists, serve it
    if file_container.preview_path:
        file_service = FileService()

        # Try local path first (for local storage or performance)
        local_path = file_service.get_local_path(file_container.preview_path)
        if local_path and os.path.exists(local_path):
            return FileResponse(path=local_path, media_type="image/png")

        # Try presigned URL (S3) - return 302 redirect
        try:
            url = file_service.get_presigned_url(file_container.preview_path)
            return RedirectResponse(url=url, status_code=302)
        except NotImplementedError:
            pass

        # Fallback: stream from storage
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

    # No preview available
    raise HTTPException(status_code=404, detail="Preview not available")


# ============================================================================
# Item-File Association Endpoints
# ============================================================================


@file_router.post("/attach")
async def attach_file_to_item(
    request: AttachFileRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Attach a file to an item with a specific role.

    Based on DocDoku PartIteration pattern (nativeCADFile, attachedFiles, geometries).
    """
    # Verify item exists
    item = db.get(Item, request.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item_type = db.get(ItemType, item.item_type_id)
    locked, locked_state = is_item_locked(db, item, item_type)
    if locked:
        raise HTTPException(
            status_code=409,
            detail=f"Item is locked in state '{locked_state or item.state}'",
        )

    # Verify file exists
    file_container = db.get(FileContainer, request.file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    # Check if already attached
    existing = (
        db.query(ItemFile)
        .filter(
            ItemFile.item_id == request.item_id,
            ItemFile.file_id == request.file_id,
        )
        .first()
    )
    if existing:
        _ensure_current_version_attachment_editable(
            db,
            item,
            file_id=existing.file_id,
            file_role=existing.file_role,
            user_id=user_id,
        )
        if request.file_role != existing.file_role:
            _ensure_current_version_attachment_editable(
                db,
                item,
                file_id=existing.file_id,
                file_role=request.file_role,
                user_id=user_id,
            )
        # Update role if different
        if existing.file_role != request.file_role:
            existing.file_role = request.file_role
            existing.description = request.description
            db.commit()
        return {"status": "updated", "id": existing.id}

    _ensure_current_version_attachment_editable(
        db,
        item,
        file_id=request.file_id,
        file_role=request.file_role,
        user_id=user_id,
    )

    # Create new attachment
    item_file = ItemFile(
        id=str(uuid.uuid4()),
        item_id=request.item_id,
        file_id=request.file_id,
        file_role=request.file_role,
        description=request.description,
    )
    db.add(item_file)
    db.commit()

    return {"status": "created", "id": item_file.id}


@file_router.get("/item/{item_id}")
async def get_item_files(
    item_id: str,
    role: Optional[str] = Query(None, description="Filter by file role"),
    db: Session = Depends(get_db),
):
    """Get all files attached to an item."""
    query = db.query(ItemFile).filter(ItemFile.item_id == item_id)
    if role:
        query = query.filter(ItemFile.file_role == role)

    item_files = query.order_by(ItemFile.sequence.asc()).all()

    result = []
    for item_file in item_files:
        file_container = db.get(FileContainer, item_file.file_id)
        if file_container:
            result.append(
                {
                    "id": item_file.id,
                    "file_id": file_container.id,
                    "filename": file_container.filename,
                    "file_role": item_file.file_role,
                    "description": item_file.description,
                    "file_type": file_container.file_type,
                    "file_size": file_container.file_size,
                    "document_type": file_container.document_type,
                    "author": file_container.author,
                    "source_system": file_container.source_system,
                    "source_version": file_container.source_version,
                    "document_version": file_container.document_version,
                    "preview_url": (
                        f"/api/v1/file/{file_container.id}/preview"
                        if file_container.preview_path
                        else None
                    ),
                    "download_url": f"/api/v1/file/{file_container.id}/download",
                }
            )

    return result


@file_router.delete("/attachment/{attachment_id}")
async def detach_file(
    attachment_id: str,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Remove file attachment from item."""
    item_file = db.get(ItemFile, attachment_id)
    if not item_file:
        raise HTTPException(status_code=404, detail="Attachment not found")

    item = db.get(Item, item_file.item_id)
    if item:
        item_type = db.get(ItemType, item.item_type_id)
        locked, locked_state = is_item_locked(db, item, item_type)
        if locked:
            raise HTTPException(
                status_code=409,
                detail=f"Item is locked in state '{locked_state or item.state}'",
            )
    _ensure_current_version_attachment_editable(
        db,
        item,
        file_id=item_file.file_id,
        file_role=item_file.file_role,
        user_id=user_id,
    )

    db.delete(item_file)
    db.commit()

    return {"status": "deleted"}
