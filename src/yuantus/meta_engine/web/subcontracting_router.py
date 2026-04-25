"""Subcontracting bootstrap API endpoints (legacy shell)."""
from __future__ import annotations

from fastapi import APIRouter

subcontracting_router = APIRouter(prefix="/subcontracting", tags=["Subcontracting"])
