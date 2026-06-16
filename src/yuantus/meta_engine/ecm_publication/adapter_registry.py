"""Resolve an EcmPublicationAdapter for a target_system.

Routing is OFF by default: the resolver returns the no-I/O Null adapter unless
``PUBLICATION_ECM_TARGET_SYSTEM`` is configured AND matches the row's
``target_system`` -- so dev/CI never accidentally performs a real external write to
Athena. The configured branch lazy-imports the real Athena Transfer Receiver
adapter (ECM-P1D retarget). The older CMIS adapter remains in-tree as a
compliance reference and is intentionally not resolved here.
"""
from __future__ import annotations

from typing import Any, Optional

from yuantus.config import get_settings
from yuantus.meta_engine.ecm_publication.adapter import (
    EcmPublicationAdapter,
    NullEcmPublicationAdapter,
)


def resolve_adapter(
    target_system: Optional[str], *, settings: Any = None
) -> EcmPublicationAdapter:
    s = settings or get_settings()
    configured = (getattr(s, "PUBLICATION_ECM_TARGET_SYSTEM", "") or "").strip()
    # Fail CLOSED to Null if there is no reachable base URL, so a half-configured
    # deployment can never spin a live adapter pointing at a bogus host (which would
    # churn the at-least-once outbox forever). Mirrors the erp resolver's base-url guard.
    base = (
        getattr(s, "PUBLICATION_ECM_BASE_URL", "")
        or getattr(s, "ATHENA_BASE_URL", "")
        or ""
    ).strip()
    if configured and base and (target_system or "").strip() == configured:
        # Lazy import so the common Null path never imports httpx / the real client.
        from yuantus.meta_engine.ecm_publication.transfer_receiver_adapter import (
            AthenaTransferReceiverAdapter,
        )

        return AthenaTransferReceiverAdapter(settings=s)
    return NullEcmPublicationAdapter()
