"""Version iteration API endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional as get_current_user_id
from yuantus.database import get_db
from yuantus.meta_engine.version.service import IterationService, VersionError

version_iteration_router = APIRouter(prefix="/versions", tags=["Versioning"])


class CreateIterationRequest(BaseModel):
    properties: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    source_type: str = "manual"


@version_iteration_router.post("/{version_id}/iterations")
def create_iteration(
    version_id: str,
    request: CreateIterationRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a new iteration within a version.
    Iterations are lightweight work-in-progress saves.
    """
    service = IterationService(db)
    try:
        iteration = service.create_iteration(
            version_id=version_id,
            user_id=user_id,
            properties=request.properties,
            description=request.description,
            source_type=request.source_type,
        )
        db.commit()
        return {
            "id": iteration.id,
            "version_id": iteration.version_id,
            "iteration_number": iteration.iteration_number,
            "iteration_label": iteration.iteration_label,
            "is_latest": iteration.is_latest,
            "source_type": iteration.source_type,
            "created_at": (
                iteration.created_at.isoformat() if iteration.created_at else None
            ),
        }
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@version_iteration_router.get("/{version_id}/iterations")
def get_iterations(version_id: str, db: Session = Depends(get_db)):
    """Get all iterations for a version."""
    service = IterationService(db)
    iterations = service.get_iterations(version_id)
    return [
        {
            "id": it.id,
            "iteration_number": it.iteration_number,
            "iteration_label": it.iteration_label,
            "is_latest": it.is_latest,
            "source_type": it.source_type,
            "description": it.description,
            "created_at": it.created_at.isoformat() if it.created_at else None,
        }
        for it in iterations
    ]


@version_iteration_router.get("/{version_id}/iterations/latest")
def get_latest_iteration(version_id: str, db: Session = Depends(get_db)):
    """Get the latest iteration for a version."""
    service = IterationService(db)
    iteration = service.get_latest_iteration(version_id)
    if not iteration:
        raise HTTPException(status_code=404, detail="No iterations found")
    return {
        "id": iteration.id,
        "iteration_number": iteration.iteration_number,
        "iteration_label": iteration.iteration_label,
        "is_latest": iteration.is_latest,
        "properties": iteration.properties,
        "description": iteration.description,
        "created_at": (
            iteration.created_at.isoformat() if iteration.created_at else None
        ),
    }


@version_iteration_router.post("/iterations/{iteration_id}/restore")
def restore_iteration(
    iteration_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Restore a previous iteration as the latest."""
    service = IterationService(db)
    try:
        iteration = service.restore_iteration(iteration_id, user_id)
        db.commit()
        return {
            "id": iteration.id,
            "iteration_number": iteration.iteration_number,
            "iteration_label": iteration.iteration_label,
            "is_latest": iteration.is_latest,
        }
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@version_iteration_router.delete("/iterations/{iteration_id}")
def delete_iteration(iteration_id: str, db: Session = Depends(get_db)):
    """Delete an iteration (not the latest one)."""
    service = IterationService(db)
    try:
        success = service.delete_iteration(iteration_id)
        if not success:
            raise HTTPException(status_code=404, detail="Iteration not found")
        db.commit()
        return {"status": "deleted"}
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
