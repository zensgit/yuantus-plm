"""
File Management API Router
Enhanced with FileContainer model and CAD conversion integration.

Based on patterns from:
- DocDoku-PLM: Vault path pattern, generated files subfolder
- Odoo PLM: Preview on save, conversion job queue
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid
from urllib.parse import quote

from yuantus.database import get_db
from yuantus.config import get_settings
from yuantus.meta_engine.models.file import (
    FileContainer,
    ItemFile,
    FileRole,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.version.file_service import VersionFileService, VersionFileError
from yuantus.api.dependencies.auth import get_current_user_id_optional

file_router = APIRouter(prefix="/file", tags=["File Management"])

# Vault base path should align with FileService local storage base path in dev.
VAULT_DIR = get_settings().LOCAL_STORAGE_PATH


# ============================================================================
# Pydantic Models
# ============================================================================


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
