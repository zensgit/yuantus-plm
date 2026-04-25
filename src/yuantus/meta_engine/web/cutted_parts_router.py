"""Cutted-parts API legacy compatibility shell."""
from __future__ import annotations

from fastapi import APIRouter


cutted_parts_router = APIRouter(prefix="/cutted-parts", tags=["Cutted Parts"])
