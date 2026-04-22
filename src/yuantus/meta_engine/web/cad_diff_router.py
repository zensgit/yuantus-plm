from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer

cad_diff_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadDiffResponse(BaseModel):
    file_id: str
    other_file_id: str
    properties: Dict[str, Any]
    cad_document_schema_version: Dict[str, Optional[int]]


def _diff_dicts(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    added = {key: after[key] for key in after.keys() - before.keys()}
    removed = {key: before[key] for key in before.keys() - after.keys()}
    changed = {
        key: {"from": before[key], "to": after[key]}
        for key in before.keys() & after.keys()
        if before[key] != after[key]
    }
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }


@cad_diff_router.get("/files/{file_id}/diff", response_model=CadDiffResponse)
def diff_cad_properties(
    file_id: str,
    other_file_id: Optional[str] = Query(
        None, description="Compare against this file id"
    ),
    other_id: Optional[str] = Query(
        None, description="Legacy alias for other_file_id"
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadDiffResponse:
    resolved_other_file_id = other_file_id or other_id
    if not resolved_other_file_id:
        raise HTTPException(
            status_code=422,
            detail="other_file_id is required",
        )

    file_container = db.get(FileContainer, file_id)
    other_container = db.get(FileContainer, resolved_other_file_id)
    if not file_container or not other_container:
        raise HTTPException(status_code=404, detail="File not found")

    before = file_container.cad_properties or {}
    after = other_container.cad_properties or {}
    return CadDiffResponse(
        file_id=file_container.id,
        other_file_id=other_container.id,
        properties=_diff_dicts(before, after),
        cad_document_schema_version={
            "from": file_container.cad_document_schema_version,
            "to": other_container.cad_document_schema_version,
        },
    )
