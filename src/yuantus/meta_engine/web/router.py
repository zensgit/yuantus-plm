from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.exceptions.handlers import PLMException
from ..models.meta_schema import ItemType
from ..schemas.aml import GenericItem
from ..services.engine import AMLEngine

meta_router = APIRouter(prefix="/aml", tags=["Meta Engine"])


# Optional import to avoid hard dependency on auth when used standalone
try:  # pragma: no cover - optional import
    from yuantus.api.dependencies.auth import get_current_user_optional as get_current_user
except Exception:  # pragma: no cover - defensive fallback
    get_current_user = None  # type: ignore


@meta_router.post("/apply", response_model=Dict[str, Any])
async def apply_item(
    aml: GenericItem = Body(..., description="AML Payload"),
    db: Session = Depends(get_db),
    current_user: Optional[Any] = Depends(get_current_user) if get_current_user else None,  # type: ignore
):
    """
    通用入口：接收 AML 请求，调用引擎执行。
    这是整个系统最重要的 API。
    """
    identity = str(getattr(current_user, "id")) if current_user else None
    roles: List[str] = []
    if current_user:
        roles = list(getattr(current_user, "roles", []) or [])
        if getattr(current_user, "is_superuser", False) and "superuser" not in roles:
            roles.append("superuser")

    engine = AMLEngine(db, identity_id=identity, roles=roles)
    try:
        result = engine.apply(aml)
        db.commit()
        return result
    except PLMException as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@meta_router.get("/metadata/{item_type_name}")
async def get_metadata(item_type_name: str, db: Session = Depends(get_db)):
    """
    前端专用：获取 Form/Grid 定义。
    前端调用此接口，知道 'Part' 有哪些字段，是否必填，UI怎么画。
    """
    item_type = db.query(ItemType).filter_by(id=item_type_name).first()
    if not item_type:
        raise HTTPException(status_code=404, detail="ItemType not found")

    return {
        "id": item_type.id,
        "label": item_type.label,
        "is_relationship": item_type.is_relationship,
        "properties": [
            {
                "name": p.name,
                "label": p.label,
                "type": p.data_type,
                "required": p.is_required,
                "length": p.length,
                "default": p.default_value,
            }
            for p in item_type.properties
        ],
    }
