from __future__ import annotations

import httpx
from typing import Any, Dict, Optional

from yuantus.config import get_settings
from yuantus.integrations.http import build_outbound_headers


class CadMLClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 30.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.CAD_ML_BASE_URL).rstrip("/")
        self._service_token = settings.CAD_ML_SERVICE_TOKEN
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
