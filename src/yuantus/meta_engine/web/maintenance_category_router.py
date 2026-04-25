"""Maintenance category API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.maintenance.service import MaintenanceService

maintenance_category_router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[str] = None
    description: Optional[str] = None


def _category_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "parent_id": c.parent_id,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@maintenance_category_router.post("/categories")
async def create_category(
    req: CategoryCreateRequest,
    db: Session = Depends(get_db),
):
    svc = MaintenanceService(db)
    cat = svc.create_category(
        name=req.name, parent_id=req.parent_id, description=req.description
    )
    db.commit()
    return _category_dict(cat)


@maintenance_category_router.get("/categories")
async def list_categories(db: Session = Depends(get_db)):
    svc = MaintenanceService(db)
    cats = svc.list_categories()
    return {"total": len(cats), "categories": [_category_dict(c) for c in cats]}
