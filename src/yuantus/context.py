from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
org_id_var: ContextVar[Optional[str]] = ContextVar("org_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


@dataclass(frozen=True)
class RequestContext:
    tenant_id: Optional[str]
    org_id: Optional[str]
    user_id: Optional[str]
    request_id: Optional[str] = None


def get_request_context() -> RequestContext:
    return RequestContext(
        tenant_id=tenant_id_var.get(),
        org_id=org_id_var.get(),
        user_id=user_id_var.get(),
        request_id=request_id_var.get(),
    )
