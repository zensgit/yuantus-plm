from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_change_log import log_cad_change

cad_properties_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadPropertiesResponse(BaseModel):
    file_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[str] = None
    source: Optional[str] = None
    cad_document_schema_version: Optional[int] = None


class CadPropertiesUpdateRequest(BaseModel):
    properties: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


@cad_properties_router.get(
    "/files/{file_id}/properties", response_model=CadPropertiesResponse
)
def get_cad_properties(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadPropertiesResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    updated_at = file_container.cad_properties_updated_at
    return CadPropertiesResponse(
        file_id=file_container.id,
        properties=file_container.cad_properties or {},
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_properties_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )


@cad_properties_router.patch(
    "/files/{file_id}/properties", response_model=CadPropertiesResponse
)
def update_cad_properties(
    file_id: str,
    payload: CadPropertiesUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadPropertiesResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    source = (payload.source or "manual").strip() or "manual"
    file_container.cad_properties = dict(payload.properties or {})
    file_container.cad_properties_source = source
    file_container.cad_properties_updated_at = datetime.utcnow()
    log_cad_change(
        db,
        file_container,
        "cad_properties_update",
        {"properties": file_container.cad_properties, "source": source},
        user,
    )
    db.add(file_container)
    db.commit()

    updated_at = file_container.cad_properties_updated_at
    return CadPropertiesResponse(
        file_id=file_container.id,
        properties=file_container.cad_properties or {},
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_properties_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )
