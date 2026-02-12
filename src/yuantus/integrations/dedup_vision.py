from __future__ import annotations

import os
import httpx
from typing import Any, Dict, Optional

from yuantus.config import get_settings
from yuantus.integrations.http import build_outbound_headers


class DedupVisionClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 30.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.DEDUP_VISION_BASE_URL).rstrip("/")
        self._service_token = settings.DEDUP_VISION_SERVICE_TOKEN
        self.timeout_s = timeout_s

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
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = await client.get("/health", headers=headers)
            resp.raise_for_status()
            return resp.json()

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
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            v2_data = {
                "mode": mode,
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
                if status not in {404, 405, 422, 503}:
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

    def index_add_sync(
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
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            with open(file_path, "rb") as f:
                files = {"file": (upload_name, f)}
                resp = client.post(
                    "/api/index/add",
                    params={"user_name": user_name, "upload_to_s3": "true" if upload_to_s3 else "false"},
                    files=files,
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
