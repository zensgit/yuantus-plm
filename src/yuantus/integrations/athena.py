from __future__ import annotations

import httpx
from typing import Optional

from yuantus.config import get_settings
from yuantus.integrations.http import build_outbound_headers


class AthenaClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 10.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ATHENA_BASE_URL).rstrip("/")
        self.timeout_s = timeout_s

    async def health(self, *, authorization: Optional[str] = None) -> dict:
        headers = build_outbound_headers(authorization=authorization).as_dict()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = await client.get("/health", headers=headers)
            resp.raise_for_status()
            return resp.json()
