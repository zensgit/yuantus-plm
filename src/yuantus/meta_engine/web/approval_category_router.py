"""Generic approval category API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, require_admin_user
from yuantus.database import get_db
from yuantus.meta_engine.approvals.service import ApprovalService
from yuantus.meta_engine.web._approval_write_transaction import transactional_write

approval_category_router = APIRouter(prefix="/approvals", tags=["Approvals"])


class ApprovalCategoryCreateRequest(BaseModel):
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


@approval_category_router.post("/categories")
def create_approval_category(
    req: ApprovalCategoryCreateRequest,
    _: CurrentUser = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    svc = ApprovalService(db)
    with transactional_write(db):
        cat = svc.create_category(
            name=req.name, parent_id=req.parent_id, description=req.description
        )
    return _category_dict(cat)


@approval_category_router.get("/categories")
def list_approval_categories(db: Session = Depends(get_db)):
    svc = ApprovalService(db)
    cats = svc.list_categories()
    return {"total": len(cats), "categories": [_category_dict(c) for c in cats]}
