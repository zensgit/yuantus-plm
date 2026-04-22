from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.exceptions.handlers import QuotaExceededError
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.web.cad_change_log import log_cad_change as _log_cad_change

cad_view_state_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadEntityNote(BaseModel):
    entity_id: int
    note: str
    color: Optional[str] = None


class CadViewStateResponse(BaseModel):
    file_id: str
    hidden_entity_ids: List[int] = Field(default_factory=list)
    notes: List[CadEntityNote] = Field(default_factory=list)
    updated_at: Optional[str] = None
    source: Optional[str] = None
    cad_document_schema_version: Optional[int] = None


class CadViewStateUpdateRequest(BaseModel):
    hidden_entity_ids: Optional[List[int]] = None
    notes: Optional[List[CadEntityNote]] = None
    source: Optional[str] = None
    refresh_preview: bool = False


def _load_cad_document_payload(file_container: FileContainer) -> Optional[Dict[str, Any]]:
    if not file_container.cad_document_path:
        return None
    file_service = FileService()
    output_stream = io.BytesIO()
    try:
        file_service.download_file(file_container.cad_document_path, output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"CAD document download failed: {exc}"
        ) from exc
    output_stream.seek(0)
    try:
        payload = json.load(output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="CAD document invalid JSON"
        ) from exc
    return payload if isinstance(payload, dict) else None


def _extract_entity_ids(document_payload: Dict[str, Any]) -> List[int]:
    entities = document_payload.get("entities")
    if not isinstance(entities, list):
        return []
    entity_ids: List[int] = []
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("id")
        if isinstance(entity_id, int):
            entity_ids.append(entity_id)
    return entity_ids


def _validate_entity_ids(
    file_container: FileContainer, entity_ids: List[int]
) -> None:
    if not entity_ids:
        return
    document_payload = _load_cad_document_payload(file_container)
    if not document_payload:
        return
    known_ids = set(_extract_entity_ids(document_payload))
    missing = sorted({eid for eid in entity_ids if eid not in known_ids})
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown CAD entity ids: {missing}",
        )


def _normalize_view_notes(notes: Optional[List[Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for note in notes or []:
        if isinstance(note, CadEntityNote):
            normalized.append(note.model_dump())
        elif isinstance(note, dict):
            normalized.append(note)
    return normalized


@cad_view_state_router.get(
    "/files/{file_id}/view-state", response_model=CadViewStateResponse
)
def get_cad_view_state(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadViewStateResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    state = file_container.cad_view_state or {}
    updated_at = file_container.cad_view_state_updated_at
    notes = state.get("notes") or []
    return CadViewStateResponse(
        file_id=file_container.id,
        hidden_entity_ids=state.get("hidden_entity_ids") or [],
        notes=_normalize_view_notes(notes),
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_view_state_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )


@cad_view_state_router.patch(
    "/files/{file_id}/view-state", response_model=CadViewStateResponse
)
def update_cad_view_state(
    file_id: str,
    payload: CadViewStateUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadViewStateResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    existing = file_container.cad_view_state or {}
    hidden_ids = (
        payload.hidden_entity_ids
        if payload.hidden_entity_ids is not None
        else existing.get("hidden_entity_ids")
    ) or []
    notes = (
        payload.notes
        if payload.notes is not None
        else existing.get("notes")
    ) or []
    notes_payload = _normalize_view_notes(notes)

    entity_ids: List[int] = []
    entity_ids.extend([int(eid) for eid in hidden_ids if isinstance(eid, int)])
    for note in notes_payload:
        entity_id = note.get("entity_id")
        if isinstance(entity_id, int):
            entity_ids.append(entity_id)
    _validate_entity_ids(file_container, entity_ids)

    source = (payload.source or file_container.cad_view_state_source or "manual").strip() or "manual"
    file_container.cad_view_state = {
        "hidden_entity_ids": hidden_ids,
        "notes": notes_payload,
    }
    file_container.cad_view_state_source = source
    file_container.cad_view_state_updated_at = datetime.utcnow()
    _log_cad_change(
        db,
        file_container,
        "cad_view_state_update",
        {
            "hidden_entity_ids": hidden_ids,
            "notes": notes_payload,
            "source": source,
            "refresh_preview": payload.refresh_preview,
        },
        user,
    )
    db.add(file_container)

    if payload.refresh_preview and file_container.is_cad_file():
        job_service = JobService(db)
        job_payload = {
            "file_id": file_container.id,
            "tenant_id": user.tenant_id,
            "org_id": user.org_id,
            "user_id": user.id,
        }
        try:
            job_service.create_job(
                task_type="cad_preview",
                payload=job_payload,
                user_id=user.id,
                priority=15,
                dedupe=True,
            )
        except QuotaExceededError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc

    db.commit()

    updated_at = file_container.cad_view_state_updated_at
    return CadViewStateResponse(
        file_id=file_container.id,
        hidden_entity_ids=hidden_ids,
        notes=notes_payload,
        updated_at=updated_at.isoformat() if updated_at else None,
        source=file_container.cad_view_state_source,
        cad_document_schema_version=file_container.cad_document_schema_version,
    )
