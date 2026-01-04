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
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import json
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
    ConversionJob,
    FileRole,
    DocumentType,
    ConversionStatus,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.file_service import FileService
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
    cad_manifest_url: Optional[str] = None
    cad_document_url: Optional[str] = None
    cad_metadata_url: Optional[str] = None
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
    cad_viewer_url: Optional[str] = None
    conversion_status: Optional[str] = None
    created_at: Optional[str] = None


class ConversionJobResponse(BaseModel):
    """Conversion job status response."""

    id: str
    source_file_id: str
    target_format: str
    operation_type: str
    status: str
    error_message: Optional[str] = None
    result_file_id: Optional[str] = None


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


def _guess_media_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    media_types = {
        ".obj": "model/obj",
        ".gltf": "model/gltf+json",
        ".glb": "model/gltf-binary",
        ".stl": "model/stl",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".json": "application/json",
        ".bin": "application/octet-stream",
    }
    return media_types.get(ext, "application/octet-stream")


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


def _serve_storage_path(storage_path: str, media_type: str, error_prefix: str):
    file_service = FileService()

    # Try local path first (for local storage or performance)
    local_path = file_service.get_local_path(storage_path)
    if local_path and os.path.exists(local_path):
        return FileResponse(path=local_path, media_type=media_type)

    # Try presigned URL (S3) - return 302 redirect
    try:
        url = file_service.get_presigned_url(storage_path)
        return RedirectResponse(url=url, status_code=302)
    except NotImplementedError:
        pass

    # Fallback: stream from storage
    try:
        output_stream = io.BytesIO()
        file_service.download_file(storage_path, output_stream)
        output_stream.seek(0)
        return StreamingResponse(
            output_stream,
            media_type=media_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"{error_prefix} download failed: {str(e)}"
        )


def _sanitize_asset_name(asset_name: str) -> str:
    safe_name = Path(asset_name).name
    if not safe_name or safe_name != asset_name:
        raise HTTPException(status_code=400, detail="Invalid asset name")
    return safe_name


def _load_manifest_payload(file_container: FileContainer) -> dict:
    file_service = FileService()
    output_stream = io.BytesIO()
    try:
        file_service.download_file(file_container.cad_manifest_path, output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"CAD manifest download failed: {exc}"
        ) from exc
    output_stream.seek(0)
    try:
        return json.load(output_stream)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail="CAD manifest invalid JSON"
        ) from exc


def _rewrite_cad_manifest_urls(
    request: Request, file_container: FileContainer, manifest: dict
) -> dict:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return manifest
    if file_container.cad_document_path:
        artifacts["document_json"] = str(
            request.url_for("get_cad_document", file_id=file_container.id)
        )
    if file_container.cad_metadata_path:
        artifacts["mesh_metadata"] = str(
            request.url_for("get_cad_metadata", file_id=file_container.id)
        )
    gltf_name = artifacts.get("mesh_gltf") or (
        Path(file_container.geometry_path).name if file_container.geometry_path else ""
    )
    if gltf_name:
        safe_name = _sanitize_asset_name(Path(gltf_name).name)
        artifacts["mesh_gltf"] = str(
            request.url_for(
                "get_cad_asset",
                file_id=file_container.id,
                asset_name=safe_name,
            )
        )
    manifest["artifacts"] = artifacts
    return manifest


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
        if generate_preview and file_container.is_cad_file():
            # Note: CADConverterService needs update to use FileService too.
            # For now, we assume it works or we fix it later.
            try:
                converter = CADConverterService(db, vault_base_path=VAULT_DIR)
                job = converter.create_conversion_job(
                    source_file_id=file_id,
                    target_format="png",
                    operation_type="preview",
                    priority=50,
                )
                # preview_url = f"/api/file/{file_id}/preview"
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

@file_router.get("/supported-formats")
async def get_supported_formats(db: Session = Depends(get_db)):
    """Get list of supported file formats and conversion capabilities."""
    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    return converter.get_supported_conversions()


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
        cad_viewer_url=_build_cad_viewer_url(
            request,
            file_id,
            file_container.cad_manifest_path,
        ),
        conversion_status=file_container.conversion_status,
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


@file_router.get("/{file_id}/geometry")
async def get_geometry(file_id: str, db: Session = Depends(get_db)):
    """Get converted geometry file for 3D viewer."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_container.geometry_path:
        raise HTTPException(status_code=404, detail="Geometry not available")

    media_type = _guess_media_type(file_container.geometry_path)
    return _serve_storage_path(
        file_container.geometry_path, media_type, error_prefix="Geometry"
    )


@file_router.get("/{file_id}/asset/{asset_name}")
async def get_geometry_asset(
    file_id: str, asset_name: str, db: Session = Depends(get_db)
):
    """Get geometry sidecar asset (e.g., mesh.bin) for glTF."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_container.geometry_path:
        raise HTTPException(status_code=404, detail="Geometry not available")

    safe_name = _sanitize_asset_name(asset_name)
    base_dir = os.path.dirname(file_container.geometry_path)
    asset_path = f"{base_dir}/{safe_name}" if base_dir else safe_name
    media_type = _guess_media_type(asset_path)
    return _serve_storage_path(
        asset_path, media_type, error_prefix="Geometry asset"
    )


@file_router.get("/{file_id}/cad_asset/{asset_name}", name="get_cad_asset")
async def get_cad_asset(
    file_id: str, asset_name: str, db: Session = Depends(get_db)
):
    """Get CADGF conversion assets (mesh.gltf, mesh.bin, etc.)."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    base_path = file_container.cad_manifest_path or file_container.geometry_path
    if not base_path:
        raise HTTPException(status_code=404, detail="CAD assets not available")

    safe_name = _sanitize_asset_name(asset_name)
    base_dir = os.path.dirname(base_path)
    asset_path = f"{base_dir}/{safe_name}" if base_dir else safe_name

    file_service = FileService()
    if not file_service.file_exists(asset_path):
        raise HTTPException(status_code=404, detail="CAD asset not available")

    media_type = _guess_media_type(asset_path)
    return _serve_storage_path(
        asset_path, media_type, error_prefix="CAD asset"
    )


@file_router.get("/{file_id}/cad_manifest")
async def get_cad_manifest(
    file_id: str,
    request: Request,
    rewrite: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Get CADGF manifest.json for 2D CAD conversions."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_manifest_path:
        raise HTTPException(status_code=404, detail="CAD manifest not available")
    if not rewrite:
        return _serve_storage_path(
            file_container.cad_manifest_path,
            _guess_media_type(file_container.cad_manifest_path),
            error_prefix="CAD manifest",
        )
    manifest = _load_manifest_payload(file_container)
    manifest = _rewrite_cad_manifest_urls(request, file_container, manifest)
    return JSONResponse(content=manifest)


@file_router.get("/{file_id}/cad_document")
async def get_cad_document(file_id: str, db: Session = Depends(get_db)):
    """Get CADGF document.json for 2D CAD conversions."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_document_path:
        raise HTTPException(status_code=404, detail="CAD document not available")
    return _serve_storage_path(
        file_container.cad_document_path,
        _guess_media_type(file_container.cad_document_path),
        error_prefix="CAD document",
    )


@file_router.get("/{file_id}/cad_metadata")
async def get_cad_metadata(file_id: str, db: Session = Depends(get_db)):
    """Get CADGF mesh_metadata.json for 2D CAD conversions."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_metadata_path:
        raise HTTPException(status_code=404, detail="CAD metadata not available")
    return _serve_storage_path(
        file_container.cad_metadata_path,
        _guess_media_type(file_container.cad_metadata_path),
        error_prefix="CAD metadata",
    )


# ============================================================================
# CAD Conversion Endpoints
# ============================================================================


@file_router.post("/{file_id}/convert", response_model=ConversionJobResponse)
async def request_conversion(
    file_id: str,
    target_format: str = Query("obj", description="Target format (obj, gltf, stl)"),
    db: Session = Depends(get_db),
):
    """
    Request CAD file conversion to viewable format.

    Creates a conversion job in the queue.
    """
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_container.is_cad_file():
        raise HTTPException(status_code=400, detail="File is not a CAD file")

    try:
        converter = CADConverterService(db, vault_base_path=VAULT_DIR)
        job = converter.create_conversion_job(
            source_file_id=file_id,
            target_format=target_format,
            operation_type="convert",
        )
        db.commit()

        return ConversionJobResponse(
            id=job.id,
            source_file_id=job.source_file_id,
            target_format=job.target_format,
            operation_type=job.operation_type,
            status=job.status,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@file_router.get("/conversion/{job_id}", response_model=ConversionJobResponse)
async def get_conversion_status(job_id: str, db: Session = Depends(get_db)):
    """Get status of a conversion job."""
    job = db.get(ConversionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Conversion job not found")

    return ConversionJobResponse(
        id=job.id,
        source_file_id=job.source_file_id,
        target_format=job.target_format,
        operation_type=job.operation_type,
        status=job.status,
        error_message=job.error_message,
        result_file_id=job.result_file_id,
    )


@file_router.get("/conversions/pending")
async def list_pending_conversions(
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db),
):
    """List pending conversion jobs."""
    jobs = (
        db.query(ConversionJob)
        .filter(
            ConversionJob.status.in_(
                [
                    ConversionStatus.PENDING.value,
                    ConversionStatus.PROCESSING.value,
                ]
            )
        )
        .order_by(ConversionJob.priority.asc(), ConversionJob.created_at.asc())
        .limit(limit)
        .all()
    )

    return [
        ConversionJobResponse(
            id=job.id,
            source_file_id=job.source_file_id,
            target_format=job.target_format,
            operation_type=job.operation_type,
            status=job.status,
            error_message=job.error_message,
            result_file_id=job.result_file_id,
        )
        for job in jobs
    ]


@file_router.post("/conversions/process")
async def process_conversion_queue(
    batch_size: int = Query(10, le=50),
    db: Session = Depends(get_db),
):
    """
    Process pending conversion jobs.

    This endpoint is typically called by a background worker.
    """
    try:
        converter = CADConverterService(db, vault_base_path=VAULT_DIR)
        results = converter.process_batch(batch_size)
        db.commit()
        return results

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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

    # Enforce file lock when version is checked out by someone else
    if item.current_version_id:
        from yuantus.meta_engine.version.models import ItemVersion

        ver = db.get(ItemVersion, item.current_version_id)
        if ver and ver.checked_out_by_id and ver.checked_out_by_id != user_id:
            raise HTTPException(
                status_code=409,
                detail=f"Version {ver.id} is checked out by another user",
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
        # Update role if different
        if existing.file_role != request.file_role:
            existing.file_role = request.file_role
            existing.description = request.description
            db.commit()
        return {"status": "updated", "id": existing.id}

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
    if item and item.current_version_id:
        from yuantus.meta_engine.version.models import ItemVersion

        ver = db.get(ItemVersion, item.current_version_id)
        if ver and ver.checked_out_by_id and ver.checked_out_by_id != user_id:
            raise HTTPException(
                status_code=409,
                detail=f"Version {ver.id} is checked out by another user",
            )

    db.delete(item_file)
    db.commit()

    return {"status": "deleted"}


# ============================================================================
# Legacy Compatibility (keeping old endpoint)
# ============================================================================


@file_router.post("/process_cad")
async def process_cad_legacy(payload: dict, db: Session = Depends(get_db)):
    """
    Legacy endpoint for triggering CAD conversion.
    Prefer using POST /{file_id}/convert instead.
    """
    file_id = payload.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing file_id")

    target_format = payload.get("target_format", "obj")

    # Try to find FileContainer
    file_container = db.get(FileContainer, file_id)
    if file_container:
        # Use new conversion system
        converter = CADConverterService(db, vault_base_path=VAULT_DIR)
        job = converter.create_conversion_job(
            source_file_id=file_id,
            target_format=target_format,
            operation_type="convert",
        )
        db.commit()
        return {
            "status": "queued",
            "job_id": job.id,
            "viewable_url": f"/api/v1/file/{file_id}/geometry",
        }

    # Fallback to old behavior for backwards compatibility
    import subprocess
    import sys

    input_path = os.path.join(VAULT_DIR, file_id)
    output_filename = f"{file_id}.obj"
    output_path = os.path.join(VAULT_DIR, output_filename)

    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="Input file not found")

    script_path = os.path.join(os.getcwd(), "scripts", "cad_converter.py")
    if os.path.exists(script_path):
        try:
            result = subprocess.run(
                [sys.executable, script_path, input_path, output_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise Exception(f"Converter failed: {result.stderr}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="Converter script not found")

    return {"status": "success", "viewable_url": f"/files/{output_filename}"}
