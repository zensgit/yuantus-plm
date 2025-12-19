from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import os

from yuantus.database import get_db
from yuantus.exceptions.handlers import PLMException
from .rpc_registry import get_handler
from yuantus.meta_engine.services.engine import AMLEngine

rpc_router = APIRouter(prefix="/rpc", tags=["Unified RPC"])

# Development mode: use admin identity for all requests
DEV_MODE = os.environ.get("PLM_DEV_MODE", "true").lower() == "true"


@rpc_router.post("/", response_model=Dict[str, Any])
async def rpc_dispatch(
    payload: Dict[str, Any] = Body(
        ..., description="{'model': str, 'method': str, 'args': [], 'kwargs': {}}"
    ),
    db: Session = Depends(get_db),
    current_user: Optional[Any] = Depends(lambda: None),
):
    """
    Unified RPC Entry Point.
    """
    model = payload.get("model")
    method = payload.get("method")
    args = payload.get("args", [])
    kwargs = payload.get("kwargs", {})

    if not model or not method:
        raise HTTPException(
            status_code=400, detail="Both 'model' and 'method' are required."
        )

    handler = get_handler(model, method)
    if handler is None:
        raise HTTPException(
            status_code=404, detail=f"RPC method '{model}.{method}' not found."
        )



    # In dev mode, use admin identity; otherwise use current_user
    if DEV_MODE:
        identity = "admin"
        roles = ["admin", "superuser"]
    else:
        identity = getattr(current_user, "id", None) if current_user else None
        roles: List[str] = []
        if current_user:
            role = getattr(current_user, "role", None)
            if role:
                roles.append(str(role))
            if getattr(current_user, "is_superuser", False):
                roles.append("superuser")

    engine = AMLEngine(db, identity_id=identity, roles=roles)

    try:
        # handler is the unbound function, likely.
        # But wait, rpc_exposed decorates AMLEngine methods.
        # If it decorates instance methods, 'self' is missing if we call `handler(args)`.
        # However, AMLEngine methods are instance methods.
        # We need to bind them or the decorator should return a wrapper that expects 'engine' as first arg?

        # In our registry design:
        # RpcHandler = Callable[[Any, List[Any], Dict[str, Any]], Any]
        # It expects the 'engine' instance as first arg?
        # Let's check engine.py implementation.
        # Yes, standard python method is (self, ...).
        # So we pass (engine, args, kwargs).

        result = handler(engine, args, kwargs)
        db.commit()
        return {"result": result}
    except PLMException as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict())
    except Exception as exc:
        import traceback

        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
