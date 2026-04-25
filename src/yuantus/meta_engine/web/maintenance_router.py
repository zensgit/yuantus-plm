"""Maintenance management API endpoints (legacy shell)."""
from __future__ import annotations

from fastapi import APIRouter

maintenance_router = APIRouter(prefix="/maintenance", tags=["Maintenance"])
