from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordHash:
    algorithm: str
    iterations: int
    salt_b64: str
    digest_b64: str

    def to_string(self) -> str:
        return f"{self.algorithm}${self.iterations}${self.salt_b64}${self.digest_b64}"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(raw_b64: str) -> bytes:
    pad = "=" * (-len(raw_b64) % 4)
    return base64.urlsafe_b64decode(raw_b64 + pad)


def hash_password(password: str, *, iterations: int = 260_000) -> str:
    if not password:
        raise ValueError("Password must not be empty")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return PasswordHash(
        algorithm="pbkdf2_sha256",
        iterations=iterations,
        salt_b64=_b64e(salt),
        digest_b64=_b64e(digest),
    ).to_string()


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = _b64d(salt_b64)
        expected = _b64d(digest_b64)
    except Exception:
        return False

    computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(computed, expected)

