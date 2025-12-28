from __future__ import annotations

import httpx
import asyncio
import time
from pathlib import Path
from typing import Optional, Tuple

from yuantus.config import get_settings
from yuantus.integrations.http import build_outbound_headers


class AthenaClient:
    def __init__(self, *, base_url: Optional[str] = None, timeout_s: float = 10.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ATHENA_BASE_URL).rstrip("/")
        self.timeout_s = timeout_s
        self.service_token = settings.ATHENA_SERVICE_TOKEN.strip()
        self.token_url = settings.ATHENA_TOKEN_URL.strip()
        self.client_id = settings.ATHENA_CLIENT_ID.strip()
        self.client_secret = settings.ATHENA_CLIENT_SECRET.strip()
        self.client_secret_file = settings.ATHENA_CLIENT_SECRET_FILE.strip()
        self.client_scope = settings.ATHENA_CLIENT_SCOPE.strip()

    def _resolve_client_secret(self) -> str:
        if self.client_secret:
            return self.client_secret
        if self.client_secret_file:
            try:
                return Path(self.client_secret_file).read_text(encoding="utf-8").strip()
            except OSError:
                return ""
        return ""

    async def _fetch_client_credentials_token(self) -> Optional[str]:
        client_secret = self._resolve_client_secret()
        if not self.token_url or not self.client_id or not client_secret:
            return None
        token, _ = await _get_cached_client_token(
            token_url=self.token_url,
            client_id=self.client_id,
            client_secret=client_secret,
            scope=self.client_scope,
            timeout_s=self.timeout_s,
        )
        return token

    async def health(
        self,
        *,
        authorization: Optional[str] = None,
        athena_authorization: Optional[str] = None,
    ) -> dict:
        auth_header = athena_authorization or authorization
        if not auth_header and self.service_token:
            auth_header = self.service_token
            if not auth_header.lower().startswith("bearer "):
                auth_header = f"Bearer {auth_header}"
        if not auth_header:
            client_token = await self._fetch_client_credentials_token()
            if client_token:
                auth_header = f"Bearer {client_token}"
        headers = build_outbound_headers(authorization=auth_header).as_dict()
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout_s) as client:
            resp = await client.get("/system/status", headers=headers)
            if resp.status_code == 404:
                resp = await client.get("/health", headers=headers)
            resp.raise_for_status()
            return resp.json()


_ATHENA_TOKEN_CACHE: dict[str, object] = {"token": None, "expires_at": 0.0}
_ATHENA_TOKEN_LOCK = asyncio.Lock()


async def _request_client_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    scope: str,
    timeout_s: float,
) -> Tuple[str, int]:
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    if scope:
        data["scope"] = scope
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(token_url, data=data)
        resp.raise_for_status()
        payload = resp.json()
    token = payload.get("access_token")
    expires_in = int(payload.get("expires_in") or 300)
    if not token:
        raise httpx.HTTPError("Missing access_token in token response")
    return token, expires_in


async def _get_cached_client_token(
    *,
    token_url: str,
    client_id: str,
    client_secret: str,
    scope: str,
    timeout_s: float,
) -> Tuple[str, int]:
    now = time.time()
    token = _ATHENA_TOKEN_CACHE.get("token")
    expires_at = float(_ATHENA_TOKEN_CACHE.get("expires_at") or 0.0)
    if token and now < (expires_at - 30):
        return token, int(expires_at - now)

    async with _ATHENA_TOKEN_LOCK:
        now = time.time()
        token = _ATHENA_TOKEN_CACHE.get("token")
        expires_at = float(_ATHENA_TOKEN_CACHE.get("expires_at") or 0.0)
        if token and now < (expires_at - 30):
            return token, int(expires_at - now)

        token, expires_in = await _request_client_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            timeout_s=timeout_s,
        )
        _ATHENA_TOKEN_CACHE["token"] = token
        _ATHENA_TOKEN_CACHE["expires_at"] = now + max(expires_in, 60)
        return token, expires_in
