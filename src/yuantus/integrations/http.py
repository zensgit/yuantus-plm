from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yuantus.context import get_request_context


@dataclass(frozen=True)
class OutboundHeaders:
    tenant_id: Optional[str]
    org_id: Optional[str]
    authorization: Optional[str]

    def as_dict(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.tenant_id:
            headers["x-tenant-id"] = self.tenant_id
        if self.org_id:
            headers["x-org-id"] = self.org_id
        if self.authorization:
            headers["Authorization"] = self.authorization
        return headers


def build_outbound_headers(*, authorization: Optional[str] = None) -> OutboundHeaders:
    ctx = get_request_context()
    return OutboundHeaders(
        tenant_id=ctx.tenant_id,
        org_id=ctx.org_id,
        authorization=authorization,
    )
