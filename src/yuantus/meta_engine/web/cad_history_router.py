from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import FileContainer

cad_history_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadChangeLogEntry(BaseModel):
    id: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    user_id: Optional[int] = None


class CadChangeLogResponse(BaseModel):
    file_id: str
    entries: List[CadChangeLogEntry]


@cad_history_router.get(
    "/files/{file_id}/history", response_model=CadChangeLogResponse
)
def get_cad_history(
    file_id: str,
    limit: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadChangeLogResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    logs = (
        db.query(CadChangeLog)
        .filter(CadChangeLog.file_id == file_container.id)
        .order_by(CadChangeLog.created_at.desc())
        .limit(limit)
        .all()
    )
    entries = [
        CadChangeLogEntry(
            id=log.id,
            action=log.action,
            payload=log.payload or {},
            created_at=log.created_at.isoformat(),
            user_id=log.user_id,
        )
        for log in logs
    ]
    return CadChangeLogResponse(file_id=file_container.id, entries=entries)
