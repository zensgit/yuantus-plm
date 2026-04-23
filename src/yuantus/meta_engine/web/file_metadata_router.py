"""
File metadata router.

This module owns the generic file metadata endpoint split out of the legacy
file router.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.cad_converter_service import CADConverterService


file_metadata_router = APIRouter(prefix="/file", tags=["File Management"])

# Vault base path should align with FileService local storage base path in dev.
VAULT_DIR = get_settings().LOCAL_STORAGE_PATH


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


def _build_cad_viewer_url(
    request: Request,
    file_id: str,
    cad_manifest_path: Optional[str],
) -> Optional[str]:
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


@file_metadata_router.get("/{file_id}", response_model=FileMetadata)
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
