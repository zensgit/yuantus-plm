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
        self.timeout_s = timeout_s

    async def health(self, *, authorization: Optional[str] = None) -> dict:
        headers = build_outbound_headers(authorization=authorization).as_dict()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = await client.get("/health", headers=headers)
            resp.raise_for_status()
            return resp.json()

    def search_sync(
        self,
        *,
        file_path: str,
        mode: str = "balanced",
        phash_threshold: int = 10,
        feature_threshold: float = 0.85,
        max_results: int = 5,
        exclude_self: bool = True,
        diff_top_k: int = 0,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call dedupcad-vision `/api/search` (v1) to find similar drawings.
        """
        headers = build_outbound_headers(authorization=authorization).as_dict()
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
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
        user_name: str,
        upload_to_s3: bool = False,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call dedupcad-vision `/api/index/add` to index a drawing.
        """
        headers = build_outbound_headers(authorization=authorization).as_dict()
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                resp = client.post(
                    "/api/index/add",
                    params={"user_name": user_name, "upload_to_s3": "true" if upload_to_s3 else "false"},
                    files=files,
                    headers=headers,
                )
                resp.raise_for_status()
                return resp.json()
