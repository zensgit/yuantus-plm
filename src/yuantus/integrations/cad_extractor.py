from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from yuantus.config import get_settings
from yuantus.integrations.http import build_outbound_headers


class CadExtractorClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 30.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.CAD_EXTRACTOR_BASE_URL).rstrip("/")
        self._service_token = settings.CAD_EXTRACTOR_SERVICE_TOKEN
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

    def extract_sync(
        self,
        *,
        file_path: str,
        filename: Optional[str] = None,
        cad_format: Optional[str] = None,
        cad_connector_id: Optional[str] = None,
        authorization: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call CAD extractor `/api/v1/extract` for attribute extraction.
        Expected response: {"ok": true, "attributes": {...}} (attributes may be empty).
        """
        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()
        name = filename or os.path.basename(file_path)
        data = {}
        if cad_format:
            data["cad_format"] = cad_format
        if cad_connector_id:
            data["cad_connector_id"] = cad_connector_id
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            with open(file_path, "rb") as f:
                files = {"file": (name, f)}
                resp = client.post("/api/v1/extract", files=files, data=data, headers=headers)
                resp.raise_for_status()
                return resp.json()
