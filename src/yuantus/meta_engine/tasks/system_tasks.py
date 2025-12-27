from __future__ import annotations

from typing import Any, Dict


def quota_test(payload: Dict[str, Any], *_args: object) -> Dict[str, Any]:
    """No-op handler for quota verification jobs."""
    return {"ok": True, "payload": payload}
