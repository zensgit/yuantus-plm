from __future__ import annotations

import os
import httpx
from typing import Any, Dict, Optional

from yuantus.config import get_settings
from yuantus.integrations.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    get_or_create_breaker,
)
from yuantus.integrations.http import build_outbound_headers


CAD_ML_BREAKER_NAME = "cad_ml"

_CAD_ML_BREAKER_COUNT_STATUS = {408, 429}


def is_cad_ml_breaker_failure(exc: Exception) -> bool:
    """P6.2 failure classification (mirrors P6.1's policy).

    Counted (upstream unhealthy):
      - `httpx.RequestError` subclasses (connect/read/timeout).
      - `httpx.HTTPStatusError` 5xx.
      - `httpx.HTTPStatusError` 408 / 429 (recoverable upstream pressure).

    NOT counted (re-raised, breaker not implicated):
      - `OSError` and subclasses — local I/O failures.
      - `httpx.HTTPStatusError` other 4xx — caller-side errors.

    Unknown exception types fall back to counting (defensive).
    """
    if isinstance(exc, OSError):
        return False
    if isinstance(exc, httpx.RequestError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        if isinstance(status, int):
            if 500 <= status < 600:
                return True
            if status in _CAD_ML_BREAKER_COUNT_STATUS:
                return True
            return False
        return True
    return True


def build_cad_ml_breaker() -> CircuitBreaker:
    settings = get_settings()
    config = CircuitBreakerConfig(
        name=CAD_ML_BREAKER_NAME,
        enabled=bool(settings.CIRCUIT_BREAKER_CAD_ML_ENABLED),
        failure_threshold=int(settings.CIRCUIT_BREAKER_CAD_ML_FAILURE_THRESHOLD),
        window_seconds=float(settings.CIRCUIT_BREAKER_CAD_ML_WINDOW_SECONDS),
        recovery_seconds=float(settings.CIRCUIT_BREAKER_CAD_ML_RECOVERY_SECONDS),
        half_open_max_calls=int(settings.CIRCUIT_BREAKER_CAD_ML_HALF_OPEN_MAX_CALLS),
        backoff_max_seconds=float(settings.CIRCUIT_BREAKER_CAD_ML_BACKOFF_MAX_SECONDS),
        is_failure=is_cad_ml_breaker_failure,
    )
    return get_or_create_breaker(config)


class CadMLClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 30.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.CAD_ML_BASE_URL).rstrip("/")
        self._service_token = settings.CAD_ML_SERVICE_TOKEN
        self.timeout_s = timeout_s
        self._breaker = build_cad_ml_breaker()

    def _resolve_authorization(self, authorization: Optional[str]) -> Optional[str]:
        token = authorization or self._service_token
        if not token:
            return None
        token = token.strip()
        if not token:
            return None
        if token.lower().startswith("bearer "):
            return token
        return f"Bearer {token}"

    async def health(self, *, authorization: Optional[str] = None) -> dict:
        return await self._breaker.call_async(
            self._health_inner, authorization=authorization
        )

    async def _health_inner(self, *, authorization: Optional[str] = None) -> dict:
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = await client.get("/api/v1/health", headers=headers)
            resp.raise_for_status()
            return resp.json()

    def vision_analyze_sync(
        self,
        *,
        image_base64: str,
        include_description: bool = True,
        include_ocr: bool = True,
        provider: Optional[str] = None,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._breaker.call_sync(
            self._vision_analyze_sync_inner,
            image_base64=image_base64,
            include_description=include_description,
            include_ocr=include_ocr,
            provider=provider,
            authorization=authorization,
        )

    def _vision_analyze_sync_inner(
        self,
        *,
        image_base64: str,
        include_description: bool = True,
        include_ocr: bool = True,
        provider: Optional[str] = None,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call cad-ml-platform `/api/v1/vision/analyze` (Vision + OCR).
        """
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        params: Dict[str, str] = {}
        if provider:
            params["provider"] = provider
        payload = {
            "image_base64": image_base64,
            "include_description": include_description,
            "include_ocr": include_ocr,
            "ocr_provider": "auto",
        }
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = client.post(
                "/api/v1/vision/analyze", json=payload, params=params, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    def ocr_extract_sync(
        self,
        *,
        file_path: str,
        filename: Optional[str] = None,
        provider: Optional[str] = None,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._breaker.call_sync(
            self._ocr_extract_sync_inner,
            file_path=file_path,
            filename=filename,
            provider=provider,
            authorization=authorization,
        )

    def _ocr_extract_sync_inner(
        self,
        *,
        file_path: str,
        filename: Optional[str] = None,
        provider: Optional[str] = None,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call cad-ml-platform `/api/v1/ocr/extract` for title-block OCR.
        """
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        params: Dict[str, str] = {}
        if provider:
            params["provider"] = provider
        name = filename or os.path.basename(file_path)
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            with open(file_path, "rb") as f:
                files = {"file": (name, f)}
                resp = client.post("/api/v1/ocr/extract", params=params, files=files, headers=headers)
                resp.raise_for_status()
                return resp.json()

    def render_cad_preview_sync(
        self,
        *,
        file_path: str,
        filename: Optional[str] = None,
        authorization: Optional[str] = None,
    ) -> bytes:
        return self._breaker.call_sync(
            self._render_cad_preview_sync_inner,
            file_path=file_path,
            filename=filename,
            authorization=authorization,
        )

    def _render_cad_preview_sync_inner(
        self,
        *,
        file_path: str,
        filename: Optional[str] = None,
        authorization: Optional[str] = None,
    ) -> bytes:
        """
        Call cad-ml-platform `/api/v1/render/cad` to render DWG/DXF previews.
        """
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        name = filename or os.path.basename(file_path)
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            with open(file_path, "rb") as f:
                files = {"file": (name, f)}
                resp = client.post("/api/v1/render/cad", files=files, headers=headers)
                resp.raise_for_status()
                return resp.content
