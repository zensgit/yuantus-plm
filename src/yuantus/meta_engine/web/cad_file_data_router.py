from __future__ import annotations

import io
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.job import ConversionJob
from yuantus.meta_engine.services.file_service import FileService

cad_file_data_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadExtractAttributesResponse(BaseModel):
    file_id: str
    cad_format: Optional[str] = None
    cad_connector_id: Optional[str] = None
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    extracted_at: Optional[str] = None
    extracted_attributes: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


class CadBomResponse(BaseModel):
    file_id: str
    item_id: Optional[str] = None
    job_id: Optional[str] = None
    job_status: Optional[str] = None
    imported_at: Optional[str] = None
    import_result: Dict[str, Any] = Field(default_factory=dict)
    bom: Dict[str, Any] = Field(default_factory=dict)


@cad_file_data_router.get(
    "/files/{file_id}/attributes", response_model=CadExtractAttributesResponse
)
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


@cad_file_data_router.get("/files/{file_id}/bom", response_model=CadBomResponse)
def get_cad_bom(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadBomResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if file_container.cad_bom_path:
        file_service = FileService()
        output_stream = io.BytesIO()
        try:
            file_service.download_file(file_container.cad_bom_path, output_stream)
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"CAD BOM download failed: {exc}"
            ) from exc
        output_stream.seek(0)
        try:
            payload = json.load(output_stream)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="CAD BOM invalid JSON") from exc
        return CadBomResponse(
            file_id=file_container.id,
            item_id=payload.get("item_id"),
            imported_at=payload.get("imported_at"),
            import_result=payload.get("import_result") or {},
            bom=payload.get("bom") or {},
            job_status="completed",
        )

    jobs = (
        db.query(ConversionJob)
        .filter(ConversionJob.task_type == "cad_bom")
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
        raise HTTPException(status_code=404, detail="No cad_bom data found")

    payload = matched_job.payload or {}
    result = payload.get("result") or {}
    imported_at = matched_job.completed_at or matched_job.created_at

    return CadBomResponse(
        file_id=file_container.id,
        item_id=payload.get("item_id"),
        job_id=matched_job.id,
        job_status=matched_job.status,
        imported_at=imported_at.isoformat() if imported_at else None,
        import_result=result.get("import_result") or {},
        bom=result.get("bom") or {},
    )
