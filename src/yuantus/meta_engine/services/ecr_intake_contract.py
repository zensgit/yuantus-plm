"""ECR intake contract (R1, pure, contract-only).

Yuantus has ECO but no Engineering Change **Request** intake: an ECO is
created already mid-pipeline. This module is the typed, validated
boundary for "someone is requesting a change" *before* it becomes an
ECO.

It mirrors the proven shape of the consumption MES contract (`6973a4c`),
the pack-and-go bridge (`c7e6fd5`), and the maintenance bridge
(`ca6755f`):

- **no DB / Session / I/O**; it imports only the ECO *enums* (the value
  domains) — never ``ECOService``, the deprecated ``ChangeService``, a
  router, the database layer, sqlalchemy, or any plugin;
- it **does not create ECOs**: the pure mapper only produces the exact
  keyword arguments ``ECOService.create_eco`` accepts. Actually invoking
  ``create_eco`` (the wiring) and any ECR persistence are separate,
  later opt-ins;
- value domains are validated against the **live** ECO enums so an
  unknown ``change_type`` / ``priority`` fails fast (the #570 review
  lesson), and a drift test fails loudly if the enums or the
  ``create_eco`` signature change.

See ``docs/DEVELOPMENT_CLAUDE_TASK_ODOO18_ECR_INTAKE_CONTRACT_20260515.md``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# Enum value domains are the single source of truth. Importing the enum
# classes (not the service / ORM session) is what makes the drift guard
# real: if these change, validation and the drift test move with them.
from yuantus.meta_engine.models.eco import ECOPriority, ECOType

CONTRACT_VERSION = "ecr-intake.v1"

_ECO_TYPE_VALUES = frozenset(t.value for t in ECOType)
_ECO_PRIORITY_VALUES = frozenset(p.value for p in ECOPriority)

# create_eco raises if eco_type == "bom" and product_id is missing. We
# mirror that invariant at the intake boundary so it fails early and
# clearly, not deep inside create_eco.
_PRODUCT_ID_REQUIRED_FOR = ECOType.BOM.value

_KEY_SEP = "\x1f"


class ChangeRequestIntake(BaseModel):
    """A validated inbound engineering change request.

    Frozen so a validated request cannot be mutated between validation
    and mapping.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    change_type: str
    product_id: Optional[str] = None
    priority: str = ECOPriority.NORMAL.value
    reason: Optional[str] = None
    requester_user_id: Optional[int] = None
    effectivity_date: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def _title_non_empty(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("title must be a non-empty string")
        return cleaned

    @field_validator("change_type")
    @classmethod
    def _known_change_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in _ECO_TYPE_VALUES:
            raise ValueError(
                f"change_type must be one of {sorted(_ECO_TYPE_VALUES)}"
            )
        return normalized

    @field_validator("priority")
    @classmethod
    def _known_priority(cls, value: str) -> str:
        normalized = (value or ECOPriority.NORMAL.value).strip().lower()
        if normalized not in _ECO_PRIORITY_VALUES:
            raise ValueError(
                f"priority must be one of {sorted(_ECO_PRIORITY_VALUES)}"
            )
        return normalized

    @field_validator("product_id", "reason")
    @classmethod
    def _blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("effectivity_date")
    @classmethod
    def _naive_utc(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    @model_validator(mode="after")
    def _bom_requires_product_id(self) -> "ChangeRequestIntake":
        if self.change_type == _PRODUCT_ID_REQUIRED_FOR and not self.product_id:
            raise ValueError(
                f"product_id is required when change_type == "
                f"{_PRODUCT_ID_REQUIRED_FOR!r} "
                "(mirrors ECOService.create_eco's own invariant)"
            )
        return self


@dataclass(frozen=True)
class EcoDraftInputs:
    """The exact keyword arguments ``ECOService.create_eco`` accepts.

    Mirrors the ``create_eco`` signature 1:1 so the drift test can
    assert alignment. ``user_id`` keeps ``None`` as-is: ``create_eco``
    already normalizes a falsy ``user_id`` to ``1`` internally
    (``user_id_int = int(user_id) if user_id else 1``), so passing
    ``None`` is correct and preserves the 1:1 mapping — there is no
    "leave unset".
    """

    name: str
    eco_type: str
    product_id: Optional[str]
    description: Optional[str]
    priority: str
    user_id: Optional[int]
    effectivity_date: Optional[datetime]

    def as_kwargs(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "eco_type": self.eco_type,
            "product_id": self.product_id,
            "description": self.description,
            "priority": self.priority,
            "user_id": self.user_id,
            "effectivity_date": self.effectivity_date,
        }


def derive_change_request_reference(intake: ChangeRequestIntake) -> str:
    """Deterministic reference for a single change request.

    Stable across retries of the same request; distinct across different
    title / change_type / product_id / requester. R1 only derives and
    records this — it does NOT enforce uniqueness (no DB, no dedupe).
    Dedupe enforcement is a separate, later opt-in.
    """

    material = _KEY_SEP.join(
        (
            intake.title,
            intake.change_type,
            intake.product_id or "",
            "" if intake.requester_user_id is None else str(intake.requester_user_id),
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def map_change_request_to_eco_draft_inputs(
    intake: ChangeRequestIntake,
) -> EcoDraftInputs:
    """Pure map: validated intake -> create_eco kwargs.

    No DB. Does **not** call ``ECOService.create_eco``. The ECO
    ``description`` is composed as the requester ``reason`` plus a
    reserved intake envelope carrying the reference + contract version.
    """

    reference = derive_change_request_reference(intake)
    envelope = (
        f"[ecr-intake contract_version={CONTRACT_VERSION} "
        f"reference={reference}]"
    )
    if intake.reason:
        description = f"{intake.reason}\n\n{envelope}"
    else:
        description = envelope

    return EcoDraftInputs(
        name=intake.title,
        eco_type=intake.change_type,
        product_id=intake.product_id,
        description=description,
        priority=intake.priority,
        user_id=intake.requester_user_id,
        effectivity_date=intake.effectivity_date,
    )
