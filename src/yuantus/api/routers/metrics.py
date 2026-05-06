from __future__ import annotations

from fastapi import APIRouter, HTTPException
from starlette.responses import PlainTextResponse

from yuantus.config import get_settings
from yuantus.observability.metrics import render_runtime_prometheus_text


router = APIRouter(tags=["Observability"])


@router.get("/metrics", response_class=PlainTextResponse)
def metrics_endpoint() -> PlainTextResponse:
    settings = get_settings()
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    text = render_runtime_prometheus_text()
    return PlainTextResponse(content=text, media_type="text/plain; version=0.0.4")
