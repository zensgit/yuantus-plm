from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/plugins/demo", tags=["plugins-demo"])


@router.get("/ping")
def ping() -> dict:
    return {"ok": True, "plugin": "yuantus-demo"}

