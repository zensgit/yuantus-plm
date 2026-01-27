from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx

from yuantus.config import get_settings
from yuantus.integrations.http import build_outbound_headers


class CadConnectorClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 60.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.CAD_CONNECTOR_BASE_URL).rstrip("/")
        self._service_token = settings.CAD_CONNECTOR_SERVICE_TOKEN
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

    def health(self) -> Dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = client.get("/health")
            resp.raise_for_status()
            return resp.json()

    def capabilities(self) -> Dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = client.get("/capabilities")
            resp.raise_for_status()
            return resp.json()

    def convert_sync(
        self,
        *,
        file_path: Optional[str] = None,
        file_url: Optional[str] = None,
        filename: Optional[str] = None,
        cad_format: Optional[str] = None,
        cad_connector_id: Optional[str] = None,
        mode: str = "all",
        tenant_id: Optional[str] = None,
        org_id: Optional[str] = None,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        authorization: Optional[str] = None,
        async_mode: bool = False,
    ) -> Dict[str, Any]:
        if not file_path and not file_url:
            raise ValueError("cad connector convert requires file_path or file_url")

        headers = build_outbound_headers(
            authorization=self._resolve_authorization(authorization)
        ).as_dict()

        data: Dict[str, Any] = {
            "mode": mode,
            "async_mode": "true" if async_mode else "false",
        }
        if file_url:
            data["file_url"] = file_url
        if cad_format:
            data["format"] = cad_format
        if cad_connector_id:
            data["cad_connector_id"] = cad_connector_id
        if tenant_id:
            data["tenant_id"] = tenant_id
        if org_id:
            data["org_id"] = org_id
        if callback_url:
            data["callback_url"] = callback_url
        if metadata:
            data["metadata"] = json.dumps(metadata, ensure_ascii=False)

        files = None
        opened = None
        if not file_url:
            resolved_name = filename or os.path.basename(file_path or "")
            opened = open(file_path or "", "rb")
            files = {"file": (resolved_name, opened)}

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout_s) as client:
                resp = client.post("/api/v1/convert", data=data, files=files, headers=headers)
                resp.raise_for_status()
                return resp.json()
        finally:
            if opened:
                opened.close()
