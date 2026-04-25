"""PLM Box API legacy compatibility shell."""
from __future__ import annotations

from fastapi import APIRouter


box_router = APIRouter(prefix="/box", tags=["PLM Box"])
