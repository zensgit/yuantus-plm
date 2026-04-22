from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user, require_admin_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.web.cad_change_log import log_cad_change

cad_review_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadReviewResponse(BaseModel):
    file_id: str
    state: Optional[str] = None
    note: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by_id: Optional[int] = None


class CadReviewRequest(BaseModel):
    state: str
    note: Optional[str] = None


@cad_review_router.get("/files/{file_id}/review", response_model=CadReviewResponse)
def get_cad_review(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadReviewResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    reviewed_at = file_container.cad_reviewed_at
    return CadReviewResponse(
        file_id=file_container.id,
        state=file_container.cad_review_state,
        note=file_container.cad_review_note,
        reviewed_at=reviewed_at.isoformat() if reviewed_at else None,
        reviewed_by_id=file_container.cad_review_by_id,
    )


@cad_review_router.post("/files/{file_id}/review", response_model=CadReviewResponse)
def update_cad_review(
    file_id: str,
    payload: CadReviewRequest,
    user: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> CadReviewResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    state = (payload.state or "").strip().lower()
    allowed_states = {"pending", "approved", "rejected"}
    if state not in allowed_states:
        raise HTTPException(status_code=400, detail=f"Invalid review state: {state}")

    file_container.cad_review_state = state
    file_container.cad_review_note = payload.note
    file_container.cad_review_by_id = user.id
    file_container.cad_reviewed_at = datetime.utcnow()
    log_cad_change(
        db,
        file_container,
        "cad_review_update",
        {"state": state, "note": payload.note},
        user,
    )
    db.add(file_container)
    db.commit()

    reviewed_at = file_container.cad_reviewed_at
    return CadReviewResponse(
        file_id=file_container.id,
        state=file_container.cad_review_state,
        note=file_container.cad_review_note,
        reviewed_at=reviewed_at.isoformat() if reviewed_at else None,
        reviewed_by_id=file_container.cad_review_by_id,
    )
