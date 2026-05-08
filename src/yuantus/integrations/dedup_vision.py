from __future__ import annotations

import os
import logging
import httpx
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from yuantus.config import get_settings
from yuantus.integrations.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    get_or_create_breaker,
)
from yuantus.integrations.http import build_outbound_headers

logger = logging.getLogger(__name__)


DEDUP_VISION_BREAKER_NAME = "dedup_vision"

# Phase 6 P6.1 — failure classification for the DedupVision breaker.
# Status codes that imply the upstream service is unhealthy / overloaded
# (i.e. "service-side" failures the breaker is meant to protect against).
# All other 4xx are treated as client-side errors and re-raised without
# implicating the breaker.
_DEDUP_VISION_BREAKER_COUNT_STATUS = {408, 429}


def is_dedup_vision_breaker_failure(exc: Exception) -> bool:
    """Decide whether `exc` should count toward the DedupVision breaker.

    Counted (suggests upstream is unhealthy):
      - `httpx.RequestError` and subclasses (connect / read / timeout).
      - `httpx.HTTPStatusError` with 5xx status.
      - `httpx.HTTPStatusError` with 408 (Request Timeout) or 429
        (Too Many Requests) — recoverable upstream pressure signals.

    NOT counted (re-raised, breaker not implicated):
      - `OSError` and subclasses (`FileNotFoundError`, `PermissionError`,
        `IsADirectoryError`, …) — local file-system failures from reading
        the upload payload, never an upstream signal.
      - `httpx.HTTPStatusError` with other 4xx (400/401/403/404/422 …) —
        these are caller-side errors (bad input, missing auth, validation)
        and must not trip protection meant for upstream outages.

    Unknown exception types fall back to counting — silent uncounted
    failures would let true outages slip through.
    """
    # Local I/O errors raised before/around the upload (e.g. caller
    # passes a path that does not exist or is unreadable) are not
    # upstream signals. httpx exceptions are NOT OSError subclasses, so
    # this branch only matches genuine local-side I/O failures.
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
            if status in _DEDUP_VISION_BREAKER_COUNT_STATUS:
                return True
            return False
        # No response status available — defensive: count.
        return True
    return True


def build_dedup_vision_breaker() -> CircuitBreaker:
    settings = get_settings()
    config = CircuitBreakerConfig(
        name=DEDUP_VISION_BREAKER_NAME,
        enabled=bool(settings.CIRCUIT_BREAKER_DEDUP_VISION_ENABLED),
        failure_threshold=int(settings.CIRCUIT_BREAKER_DEDUP_VISION_FAILURE_THRESHOLD),
        window_seconds=float(settings.CIRCUIT_BREAKER_DEDUP_VISION_WINDOW_SECONDS),
        recovery_seconds=float(settings.CIRCUIT_BREAKER_DEDUP_VISION_RECOVERY_SECONDS),
        half_open_max_calls=int(
            settings.CIRCUIT_BREAKER_DEDUP_VISION_HALF_OPEN_MAX_CALLS
        ),
        backoff_max_seconds=float(
            settings.CIRCUIT_BREAKER_DEDUP_VISION_BACKOFF_MAX_SECONDS
        ),
        is_failure=is_dedup_vision_breaker_failure,
    )
    return get_or_create_breaker(config)


class DedupVisionClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 30.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.DEDUP_VISION_BASE_URL).rstrip("/")
        self._service_token = settings.DEDUP_VISION_SERVICE_TOKEN
        self.timeout_s = timeout_s
        self._breaker = build_dedup_vision_breaker()

    def _fallback_base_url(self) -> Optional[str]:
        explicit = (os.environ.get("YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL") or "").strip()
        if explicit:
            return explicit.rstrip("/")

        parsed = urlparse(self.base_url)
        host = (parsed.hostname or "").strip().lower()
        # Only apply host-network fallback when configured to use the compose service host.
        if host not in {"dedup-vision", "yuantus-dedup-vision"}:
            return None
        scheme = parsed.scheme or "http"
        fallback_port = (
            (os.environ.get("YUANTUS_DEDUP_VISION_FALLBACK_PORT") or "").strip()
            or (os.environ.get("DEDUP_VISION_PORT") or "").strip()
            or "8100"
        )
        return f"{scheme}://host.docker.internal:{fallback_port}"

    def _candidate_base_urls(self) -> list[str]:
        urls = [self.base_url]
        fallback = self._fallback_base_url()
        if fallback and fallback not in urls:
            urls.append(fallback)
        return urls

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
        last_error: Optional[Exception] = None
        base_urls = self._candidate_base_urls()
        for i, base_url in enumerate(base_urls):
            try:
                async with httpx.AsyncClient(base_url=base_url, timeout=self.timeout_s) as client:
                    resp = await client.get("/health", headers=headers)
                    resp.raise_for_status()
                    return resp.json()
            except httpx.RequestError as exc:
                last_error = exc
                if i + 1 < len(base_urls):
                    logger.warning(
                        "Dedup Vision request failed; retrying fallback endpoint "
                        "(primary_base_url=%s fallback_base_url=%s error_type=%s)",
                        base_url,
                        base_urls[i + 1],
                        type(exc).__name__,
                    )
                    continue
                raise
        assert last_error is not None
        raise last_error

    def search_sync(
        self,
        *,
        file_path: str,
        upload_filename: Optional[str] = None,
        mode: str = "balanced",
        phash_threshold: int = 10,
        feature_threshold: float = 0.85,
        max_results: int = 5,
        exclude_self: bool = True,
        diff_top_k: int = 0,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._breaker.call_sync(
            self._search_sync_inner,
            file_path=file_path,
            upload_filename=upload_filename,
            mode=mode,
            phash_threshold=phash_threshold,
            feature_threshold=feature_threshold,
            max_results=max_results,
            exclude_self=exclude_self,
            diff_top_k=diff_top_k,
            authorization=authorization,
        )

    def _search_sync_inner(
        self,
        *,
        file_path: str,
        upload_filename: Optional[str] = None,
        mode: str = "balanced",
        phash_threshold: int = 10,
        feature_threshold: float = 0.85,
        max_results: int = 5,
        exclude_self: bool = True,
        diff_top_k: int = 0,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call dedupcad-vision search API to find similar drawings.

        Prefer `/api/v2/search` (progressive engine) when available because it supports
        incremental indexing (new drawings are immediately queryable after `/api/index/add`).
        Fall back to legacy `/api/search` (v1) for older deployments.
        """
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        upload_name = upload_filename or os.path.basename(file_path)
        # Backward-compat: some callers use "accurate" (legacy v1 search) while v2 expects "precise".
        v2_mode = "precise" if str(mode).strip().lower() == "accurate" else mode
        last_error: Optional[Exception] = None
        base_urls = self._candidate_base_urls()
        for i, base_url in enumerate(base_urls):
            try:
                with httpx.Client(base_url=base_url, timeout=self.timeout_s) as client:
                    v2_data = {
                        "mode": v2_mode,
                        "max_results": str(max_results),
                        "compute_diff": "false",
                        "exclude_self": "true" if exclude_self else "false",
                        "enable_ml": "false",
                        "enable_geometric": "false",
                    }
                    try:
                        with open(file_path, "rb") as f:
                            files = {"file": (upload_name, f)}
                            resp = client.post("/api/v2/search", files=files, data=v2_data, headers=headers)
                        resp.raise_for_status()
                        return resp.json()
                    except httpx.HTTPStatusError as exc:
                        status = exc.response.status_code if exc.response else None
                        if status not in {400, 404, 405, 422, 503}:
                            raise

                    with open(file_path, "rb") as f:
                        files = {"file": (upload_name, f)}
                        data = {
                            "mode": mode,
                            "phash_threshold": str(phash_threshold),
                            "feature_threshold": str(feature_threshold),
                            "max_results": str(max_results),
                            "exclude_self": "true" if exclude_self else "false",
                            "diff_top_k": str(diff_top_k),
                        }
                        resp = client.post("/api/search", files=files, data=data, headers=headers)
                    resp.raise_for_status()
                    return resp.json()
            except httpx.RequestError as exc:
                last_error = exc
                if i + 1 < len(base_urls):
                    logger.warning(
                        "Dedup Vision request failed; retrying fallback endpoint "
                        "(primary_base_url=%s fallback_base_url=%s error_type=%s)",
                        base_url,
                        base_urls[i + 1],
                        type(exc).__name__,
                    )
                    continue
                raise
        assert last_error is not None
        raise last_error

    def index_add_sync(
        self,
        *,
        file_path: str,
        upload_filename: Optional[str] = None,
        user_name: str,
        upload_to_s3: bool = False,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._breaker.call_sync(
            self._index_add_sync_inner,
            file_path=file_path,
            upload_filename=upload_filename,
            user_name=user_name,
            upload_to_s3=upload_to_s3,
            authorization=authorization,
        )

    def _index_add_sync_inner(
        self,
        *,
        file_path: str,
        upload_filename: Optional[str] = None,
        user_name: str,
        upload_to_s3: bool = False,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call dedupcad-vision `/api/index/add` to index a drawing.
        """
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        upload_name = upload_filename or os.path.basename(file_path)
        last_error: Optional[Exception] = None
        base_urls = self._candidate_base_urls()
        for i, base_url in enumerate(base_urls):
            try:
                with httpx.Client(base_url=base_url, timeout=self.timeout_s) as client:
                    with open(file_path, "rb") as f:
                        files = {"file": (upload_name, f)}
                        resp = client.post(
                            "/api/index/add",
                            params={
                                "user_name": user_name,
                                "upload_to_s3": "true" if upload_to_s3 else "false",
                            },
                            files=files,
                            headers=headers,
                        )
                        resp.raise_for_status()
                        return resp.json()
            except httpx.RequestError as exc:
                last_error = exc
                if i + 1 < len(base_urls):
                    logger.warning(
                        "Dedup Vision request failed; retrying fallback endpoint "
                        "(primary_base_url=%s fallback_base_url=%s error_type=%s)",
                        base_url,
                        base_urls[i + 1],
                        type(exc).__name__,
                    )
                    continue
                raise
        assert last_error is not None
        raise last_error
