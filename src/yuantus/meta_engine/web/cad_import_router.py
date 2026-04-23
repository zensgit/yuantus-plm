from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileRole
from yuantus.meta_engine.services.cad_import_service import (
    CadImportError,
    CadImportRequest,
    CadImportService,
)
from yuantus.security.auth.database import get_identity_db

cad_import_router = APIRouter(prefix="/cad", tags=["CAD"])

"""
CAD Connector API
Handles Document Locking and Versioning.
"""


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
    cad_bom_url: Optional[str] = None
    cad_dedup_url: Optional[str] = None
    cad_viewer_url: Optional[str] = None
    cad_document_schema_version: Optional[int] = None
    cad_format: Optional[str] = None
    cad_connector_id: Optional[str] = None
    document_type: Optional[str] = None
    is_native_cad: bool = False
    author: Optional[str] = None
    source_system: Optional[str] = None
    source_version: Optional[str] = None
    document_version: Optional[str] = None


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


def _append_quota_warning(response: Response, message: str) -> None:
    if not message:
        return
    current = response.headers.get("X-Quota-Warning")
    response.headers["X-Quota-Warning"] = f"{current}; {message}" if current else message


@cad_import_router.post("/import", response_model=CadImportResponse)
async def import_cad(
    response: Response,
    request: Request,
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
    create_geometry_job: Optional[bool] = Form(default=None),
    geometry_format: str = Form(default="gltf", description="obj|gltf|glb|stl"),
    create_extract_job: Optional[bool] = Form(
        default=None,
        description="Extract CAD attributes for sync (default: true)",
    ),
    create_bom_job: bool = Form(
        default=False,
        description="Extract BOM structure from CAD (connector)",
    ),
    auto_create_part: bool = Form(
        default=False,
        description="Auto-create Part when item_id is not provided",
    ),
    create_dedup_job: bool = Form(default=False),
    dedup_mode: str = Form(default="balanced", description="fast|balanced|precise"),
    dedup_index: bool = Form(
        default=False,
        description="Index drawing into Dedup Vision after search (recommended for first-time ingest)",
    ),
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
    import_request = CadImportRequest(
        filename=file.filename or "",
        content=content,
        item_id=item_id,
        file_role=file_role,
        author=author,
        source_system=source_system,
        source_version=source_version,
        document_version=document_version,
        cad_format=cad_format,
        cad_connector_id=cad_connector_id,
        create_preview_job=create_preview_job,
        create_geometry_job=create_geometry_job,
        geometry_format=geometry_format,
        create_extract_job=create_extract_job,
        create_bom_job=create_bom_job,
        auto_create_part=auto_create_part,
        create_dedup_job=create_dedup_job,
        dedup_mode=dedup_mode,
        dedup_index=dedup_index,
        create_ml_job=create_ml_job,
        authorization=request.headers.get("authorization"),
    )

    try:
        result = CadImportService(db, identity_db).import_file(import_request, user)
    except CadImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    for warning in result.quota_warnings:
        _append_quota_warning(response, warning)

    file_container = result.file_container
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
    cad_bom_url = (
        f"/api/v1/file/{file_container.id}/cad_bom"
        if file_container.cad_bom_path
        else None
    )
    cad_dedup_url = (
        f"/api/v1/file/{file_container.id}/cad_dedup"
        if file_container.cad_dedup_path
        else None
    )
    cad_viewer_url = _build_cad_viewer_url(
        request,
        file_container.id,
        file_container.cad_manifest_path,
    )
    return CadImportResponse(
        file_id=file_container.id,
        filename=file_container.filename,
        checksum=file_container.checksum,
        is_duplicate=result.is_duplicate,
        item_id=result.item_id,
        attachment_id=result.attachment_id,
        jobs=[
            CadImportJob(id=job.id, task_type=job.task_type, status=job.status)
            for job in result.jobs
        ],
        download_url=f"/api/v1/file/{file_container.id}/download",
        preview_url=preview_url,
        geometry_url=geometry_url,
        cad_manifest_url=cad_manifest_url,
        cad_document_url=cad_document_url,
        cad_metadata_url=cad_metadata_url,
        cad_bom_url=cad_bom_url,
        cad_dedup_url=cad_dedup_url,
        cad_viewer_url=cad_viewer_url,
        cad_document_schema_version=file_container.cad_document_schema_version,
        cad_format=file_container.cad_format,
        cad_connector_id=file_container.cad_connector_id,
        document_type=file_container.document_type,
        is_native_cad=file_container.is_native_cad,
        author=file_container.author,
        source_system=file_container.source_system,
        source_version=file_container.source_version,
        document_version=file_container.document_version,
    )
