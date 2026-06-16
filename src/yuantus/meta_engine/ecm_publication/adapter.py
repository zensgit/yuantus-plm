"""PLM->ECM (Athena controlled-record) publication adapter interface (ECM-P1C).

The abstract seam an ECM/CMIS adapter implements, mirroring
``erp_publication/adapter.py`` (ABC + @abstractmethod, the repo idiom). The
concrete real Athena CMIS adapter is a LATER, separate slice (P1D, gated on
Phase 0 U1-U5); P1C ships only the no-I/O Null adapter so the full outbox state
machine is exercisable end to end without any external write.

``dry_run`` is intentionally NOT a method here. Dry-run is an outbox-SERVICE
operation that calls build_payload + validate_contract only and never ``send`` --
structurally guaranteeing dry-run produces no external side effect.

These dataclasses are DEFINED LOCALLY (not imported from erp_publication): the
two packages are intentionally parallel seams, exactly as ``ecm_publication``
re-declares its own ``EcmPublicationState`` / ``EcmPublicationReason`` enums.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class SendResult:
    ok: bool
    remote_id: Optional[str] = None
    error: Optional[str] = None
    # When ok is False: which reason the outbox should record. Defaults to
    # remote_error; an exception escaping send() is classified adapter_error.
    error_kind: Optional[str] = None


class EcmPublicationAdapter(ABC):
    """Abstract base for an ECM (Athena/CMIS) publication adapter."""

    @abstractmethod
    def build_payload(self, snapshot: dict) -> dict:
        """Build the target-ECM (CMIS) payload from the outbox snapshot. LOCAL,
        no network."""

    @abstractmethod
    def validate_contract(self, payload: dict) -> ValidationResult:
        """Validate the payload against the target contract WITHOUT any external call."""

    @abstractmethod
    def send(self, payload: dict) -> SendResult:
        """Dispatch the payload to the target ECM (the only external-write entry point)."""


class NullEcmPublicationAdapter(EcmPublicationAdapter):
    """In-repo, no-external-I/O adapter.

    The ONLY path that can reach ``sent`` before the real CMIS connector (P1D):
    ``send`` records the dispatch LOCALLY (no network, no external write) so the
    full outbox state machine is exercisable end to end. ``sent`` via this
    adapter explicitly does NOT mean Athena received anything; production
    ``sent`` requires the deferred real-connector taskbook (P1D, Phase-0-gated).
    """

    def build_payload(self, snapshot: dict) -> dict:
        # ECM snapshots are FLAT (see ecm_publication/service.build_snapshot):
        # read top-level keys, NOT erp's nested snapshot["item"]/["version"].
        return {
            "target_system": snapshot.get("target_system"),
            "item_id": snapshot.get("item_id"),
            "version_id": snapshot.get("version_id"),
            "file_id": snapshot.get("file_id"),
            "file_role": snapshot.get("file_role"),
            "snapshot": snapshot,
        }

    def validate_contract(self, payload: dict) -> ValidationResult:
        # The full per-file identity 5-tuple = the ECM idempotency key.
        errors: List[str] = []
        for key in ("item_id", "version_id", "file_id", "file_role", "target_system"):
            if not payload.get(key):
                errors.append(f"missing {key}")
        return ValidationResult(ok=not errors, errors=errors)

    def send(self, payload: dict) -> SendResult:
        # No external I/O: acknowledge locally with a deterministic, PER-FILE id
        # (a released version may have several controlled files -- a version-only
        # id would collide across them).
        remote_id = "null:" + ":".join(
            str(payload.get(k) or "")
            for k in ("item_id", "version_id", "file_id", "file_role")
        )
        return SendResult(ok=True, remote_id=remote_id)
