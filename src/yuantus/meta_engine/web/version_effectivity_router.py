"""Version effectivity and read API endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.version.service import VersionService

version_effectivity_router = APIRouter(prefix="/versions", tags=["Versioning"])


@version_effectivity_router.post("/{version_id}/effectivity")
def add_effectivity(
    version_id: str,
    start_date: datetime = Body(...),
    end_date: Optional[datetime] = Body(None),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    eff = service.add_date_effectivity(version_id, start_date, end_date)
    db.commit()
    return eff


@version_effectivity_router.get("/items/{item_id}/effective")
def get_effective_version(
    item_id: str, date: datetime = None, db: Session = Depends(get_db)
):
    if not date:
        date = datetime.utcnow()
    service = VersionService(db)
    ver = service.find_effective_version(item_id, date)
    if not ver:
        raise HTTPException(status_code=404, detail="No effective version found")
    return ver


@version_effectivity_router.get("/items/{item_id}/tree")
def get_version_tree(item_id: str, db: Session = Depends(get_db)):
    service = VersionService(db)
    return service.get_version_tree(item_id)
