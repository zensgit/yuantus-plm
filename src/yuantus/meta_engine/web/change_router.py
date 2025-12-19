from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.services.change_service import ChangeService

from yuantus.api.dependencies.auth import get_current_user_id_optional as get_current_user_id


change_router = APIRouter(prefix="/api/ecm", tags=["Change Management"])


@change_router.get("/items/{item_id}/impact")
def get_impact_analysis(item_id: str, db: Session = Depends(get_db)):
    service = ChangeService(db)
    return service.get_impact_analysis(item_id)


@change_router.get("/eco/{eco_id}/affected-items")
def get_affected_items(eco_id: str, db: Session = Depends(get_db)):
    service = ChangeService(db)
    items = service.get_affected_items(eco_id)
    return [item.to_dict() for item in items]


@change_router.post("/eco/{eco_id}/affected-items")
def add_affected_item(
    eco_id: str,
    target_item_id: str = Body(..., embed=True),
    action: str = Body("Change", embed=True),
    db: Session = Depends(get_db),
):
    service = ChangeService(db)
    try:
        item = service.add_affected_item(eco_id, target_item_id, action)
        db.commit()
        return item.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@change_router.post("/eco/{eco_id}/execute")
def execute_eco(
    eco_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Execute an ECO with authenticated user."""
    service = ChangeService(db)
    try:
        service.execute_eco(eco_id, user_id)
        db.commit()
        return {"status": "success", "message": f"ECO {eco_id} executed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
