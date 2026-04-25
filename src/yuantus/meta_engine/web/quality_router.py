"""Quality API legacy compatibility shell."""
from __future__ import annotations

from fastapi import APIRouter

quality_router = APIRouter(prefix="/quality", tags=["Quality"])
