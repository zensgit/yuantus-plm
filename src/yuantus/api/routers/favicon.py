from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(tags=["Favicon"])


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)
