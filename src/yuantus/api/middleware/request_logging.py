from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from yuantus.config import get_settings
from yuantus.context import (
    org_id_var,
    request_id_var,
    tenant_id_var,
    user_id_var,
)


_logger = logging.getLogger("yuantus.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        header_name = settings.REQUEST_ID_HEADER
        incoming = request.headers.get(header_name)
        request_id = incoming or uuid.uuid4().hex
        token = request_id_var.set(request_id)

        start = time.perf_counter()
        status_code = 500
        error: Optional[str] = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[header_name] = request_id
            return response
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            try:
                latency_ms = int((time.perf_counter() - start) * 1000)
                fields = {
                    "request_id": request_id,
                    "tenant_id": tenant_id_var.get(),
                    "org_id": org_id_var.get(),
                    "user_id": user_id_var.get(),
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                }
                if error is not None:
                    fields["error"] = error
                _emit(settings.LOG_FORMAT, fields)
            except Exception:
                pass
            finally:
                request_id_var.reset(token)


def _emit(log_format: str, fields: dict) -> None:
    if log_format == "json":
        _logger.info(json.dumps(fields, default=str))
        return
    pairs = " ".join(f"{k}={fields[k]}" for k in fields if fields[k] is not None)
    _logger.info(pairs)
