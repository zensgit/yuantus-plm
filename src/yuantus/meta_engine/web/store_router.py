from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional

from yuantus.database import get_db
from yuantus.meta_engine.app_framework.store_service import AppStoreService

store_router = APIRouter(prefix="/api/store", tags=["App Store"])


@store_router.post("/sync")
def sync_store(db: Session = Depends(get_db)):
    service = AppStoreService(db)
    service.sync_store_listings()
    db.commit()
    return {"status": "synced"}


@store_router.get("/apps")
@store_router.get("/search")  # Alias for frontend convenience
def search_apps(
    q: Optional[str] = None,  # Alias for query
    query: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    service = AppStoreService(db)
    # Support 'q' or 'query'
    qs = q or query
    apps = service.search_apps(qs, category)
    return apps


@store_router.post("/purchase")
def purchase_app(
    listing_id: str = Body(..., embed=True),
    plan: str = Body("Standard", embed=True),
    db: Session = Depends(get_db),
):
    service = AppStoreService(db)
    try:
        lic = service.purchase_app(listing_id, plan)
        db.commit()
        return {"license_key": lic.license_key, "status": lic.status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@store_router.post("/install")
def install_app(
    listing_id: str = Body(..., embed=True),
    user_id: int = Body(1, embed=True),
    db: Session = Depends(get_db),
):
    service = AppStoreService(db)
    try:
        res = service.install_from_store(listing_id, user_id)
        db.commit()
        return res
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@store_router.post("/install/{listing_id}")
def install_app_path(
    listing_id: str, user_id: int = Body(1, embed=True), db: Session = Depends(get_db)
):
    # Frontend calls /api/store/install/{id}
    return install_app(listing_id, user_id, db)
