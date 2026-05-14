"""
ECO stage administration router.

Owns the stage configuration endpoints split out of the legacy ECO router.
Kanban and ECO lifecycle operations remain in `eco_router.py`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.services.eco_service import ECOStageService


eco_stage_router = APIRouter(prefix="/eco", tags=["ECO"])


class StageCreate(BaseModel):
    """Schema for creating a stage."""

    name: str = Field(..., min_length=1, max_length=100)
    sequence: Optional[int] = None
    approval_type: str = Field(default="none")
    approval_roles: Optional[List[str]] = None
    is_blocking: bool = False
    auto_progress: bool = False
    sla_hours: Optional[int] = None
    description: Optional[str] = None


class StageUpdate(BaseModel):
    """Schema for updating a stage."""

    name: Optional[str] = None
    sequence: Optional[int] = None
    approval_type: Optional[str] = None
    approval_roles: Optional[List[str]] = None
    is_blocking: Optional[bool] = None
    auto_progress: Optional[bool] = None
    sla_hours: Optional[int] = None
    description: Optional[str] = None


@eco_stage_router.get("/stages", response_model=List[Dict[str, Any]])
async def list_stages(db: Session = Depends(get_db)):
    """List all ECO stages."""
    service = ECOStageService(db)
    stages = service.list_stages()
    return [
        {
            "id": s.id,
            "name": s.name,
            "sequence": s.sequence,
            "approval_type": s.approval_type,
            "approval_roles": s.approval_roles,
            "sla_hours": s.sla_hours,
            "is_blocking": s.is_blocking,
            "auto_progress": s.auto_progress,
            "fold": s.fold,
            "description": s.description,
        }
        for s in stages
    ]


@eco_stage_router.post("/stages", response_model=Dict[str, Any])
async def create_stage(data: StageCreate, db: Session = Depends(get_db)):
    """Create a new ECO stage."""
    service = ECOStageService(db)
    try:
        stage = service.create_stage(
            name=data.name,
            sequence=data.sequence,
            approval_type=data.approval_type,
            approval_roles=data.approval_roles,
            is_blocking=data.is_blocking,
            auto_progress=data.auto_progress,
            sla_hours=data.sla_hours,
            description=data.description,
        )
        db.commit()
        return {
            "id": stage.id,
            "name": stage.name,
            "sequence": stage.sequence,
            "approval_type": stage.approval_type,
            "sla_hours": stage.sla_hours,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_stage_router.put("/stages/{stage_id}", response_model=Dict[str, Any])
async def update_stage(stage_id: str, data: StageUpdate, db: Session = Depends(get_db)):
    """Update an ECO stage."""
    service = ECOStageService(db)
    try:
        if hasattr(data, "model_dump"):
            update_data = data.model_dump(exclude_unset=True)
        else:
            update_data = data.dict(exclude_unset=True)
        stage = service.update_stage(stage_id, **update_data)
        db.commit()
        return {
            "id": stage.id,
            "name": stage.name,
            "sequence": stage.sequence,
            "approval_type": stage.approval_type,
            "sla_hours": stage.sla_hours,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@eco_stage_router.delete("/stages/{stage_id}")
async def delete_stage(stage_id: str, db: Session = Depends(get_db)):
    """Delete an ECO stage."""
    service = ECOStageService(db)
    try:
        success = service.delete_stage(stage_id)
        if not success:
            raise HTTPException(status_code=404, detail="Stage not found")
        db.commit()
        return {"success": True, "message": "Stage deleted"}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e
