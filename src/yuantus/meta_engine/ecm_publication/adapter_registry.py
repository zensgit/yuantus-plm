"""Resolve an EcmPublicationAdapter for a target_system (ECM-P1C).

In P1C the SOLE return is the no-I/O Null adapter -- so dev/CI never accidentally
performs a real external write to Athena. The settings-gated branch that would
return the real Athena CMIS adapter is the P1D EXTENSION POINT and is deliberately
NOT wired here: the real connector is DEFERRED until Phase 0 (U1-U5) per the P0
refresh taskbook (D6) and does not yet exist, so importing/returning it now would
fail.
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
    # get_settings() is read for forward-compatibility with the P1D gate; the
    # `settings` kwarg lets tests inject a SimpleNamespace.
    _ = settings or get_settings()
    # P1D EXTENSION POINT (deferred): when the real Athena CMIS connector lands,
    # gate it here on the configured ECM target + CMIS base-url matching
    # `target_system`, and lazy-import the real adapter so the common Null path
    # never imports the CMIS client. Until then, always Null.
    return NullEcmPublicationAdapter()
