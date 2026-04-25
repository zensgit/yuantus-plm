"""Generic approvals API endpoints (legacy shell)."""
from __future__ import annotations

from fastapi import APIRouter

approvals_router = APIRouter(prefix="/approvals", tags=["Approvals"])
