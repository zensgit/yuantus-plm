from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


class JWTError(ValueError):
    pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def encode_hs256(payload: Dict[str, Any], *, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(sig)}"


def decode_hs256(token: str, *, secret: str, leeway_seconds: int = 0) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".", 2)
    except ValueError as e:
        raise JWTError("Invalid token format") from e

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as e:
        raise JWTError("Invalid token encoding") from e

    if header.get("alg") != "HS256":
        raise JWTError("Unsupported alg")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        got = _b64url_decode(sig_b64)
    except Exception as e:
        raise JWTError("Invalid signature encoding") from e
    if not hmac.compare_digest(expected, got):
        raise JWTError("Invalid signature")

    exp = payload.get("exp")
    if exp is not None:
        try:
            exp_int = int(exp)
        except Exception as e:
            raise JWTError("Invalid exp claim") from e
        now = int(time.time())
        if now > exp_int + int(leeway_seconds):
            raise JWTError("Token expired")

    return payload


def now_ts() -> int:
    return int(time.time())


def build_access_token_payload(
    *,
    user_id: int,
    tenant_id: str,
    org_id: Optional[str] = None,
    ttl_seconds: int = 3600,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    issued_at = now_ts()
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "iat": issued_at,
        "exp": issued_at + int(ttl_seconds),
    }
    if org_id:
        payload["org_id"] = org_id
    if extra:
        payload.update(extra)
    return payload

