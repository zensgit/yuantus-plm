"""Version API legacy compatibility shell."""
from __future__ import annotations

from fastapi import APIRouter

version_router = APIRouter(prefix="/versions", tags=["Versioning"])
