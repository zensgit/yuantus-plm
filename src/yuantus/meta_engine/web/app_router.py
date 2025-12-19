from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any

from yuantus.database import get_db
from yuantus.meta_engine.app_framework.service import AppService

from yuantus.api.dependencies.auth import get_current_user_id_optional as get_current_user_id


app_router = APIRouter(prefix="/api/apps", tags=["App Framework"])


@app_router.post("/register")
def register_app(
    manifest: Dict[str, Any] = Body(...),
    installer_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Register an application with authenticated user as installer."""
    service = AppService(db)
    try:
        app = service.register_app(manifest, installer_id)
        db.commit()
        return {"status": "success", "app_id": app.id, "name": app.name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@app_router.get("/extensions/{point_name}")
def get_extensions(point_name: str, db: Session = Depends(get_db)):
    service = AppService(db)
    exts = service.get_extensions_for_point(point_name)
    return [
        {
            "id": e.id,
            "name": e.name,
            "handler": e.handler,
            "config": e.config,
            "app_name": e.app.name,
        }
        for e in exts
    ]


@app_router.post("/points")
def create_point(
    name: str = Body(..., embed=True),
    description: str = Body("", embed=True),
    db: Session = Depends(get_db),
):
    service = AppService(db)
    try:
        ep = service.create_extension_point(name, description)
        db.commit()
        return {"id": ep.id, "name": ep.name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
