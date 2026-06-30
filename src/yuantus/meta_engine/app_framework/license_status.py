"""Read-only license/entitlement status for the offline support bundle (Phase 4).

A tenant-scoped, read-only summary of which collaboration SKUs a tenant currently
holds -- computed via the centralized ``EntitlementService.is_entitled`` (NOT a second,
unscoped auth path; "entitlement is centralized" is a non-negotiable invariant) -- plus
a WHITELISTED summary of its ``AppLicense`` rows. It never emits private key material or
the raw ``license_data`` blob, so it is safe to print in an operator support bundle.

Driven by ``yuantus license status --tenant-id <tenant>``; no route, no mutation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.context import tenant_id_var
from yuantus.meta_engine.app_framework.entitlement_service import (
    FEATURE_APP_NAMES,
    EntitlementService,
)
from yuantus.meta_engine.app_framework.store_models import AppLicense


@dataclass
class LicenseRowStatus:
    """A single ``AppLicense`` row, reduced to operator-safe fields only."""

    app_name: str
    status: str
    plan_type: Optional[str]
    expires_at: Optional[str]  # ISO-8601, or None for a perpetual license
    license_key: str


@dataclass
class LicenseStatus:
    tenant_id: str
    features: Dict[str, bool]  # lit feature_key -> entitled (via is_entitled)
    # Explicit, read-only edition label. Derived ONLY from `features` (the is_entitled
    # output), NEVER from plan_type, and never an authorization input. The fail-closed
    # default is "Community"; it can never report "Enterprise" or grant on a bare license.
    edition: str = "Community"
    licenses: List[LicenseRowStatus] = field(default_factory=list)


# The lit (license-unlockable) SKUs. Reserved keys map to an empty app-name set and are
# always False, so they are not reported as sellable features.
_LIT_FEATURES = tuple(sorted(k for k, apps in FEATURE_APP_NAMES.items() if apps))


def _derive_edition(features: Dict[str, bool]) -> str:
    """Explicit edition label, a PURE function of is_entitled output (never plan_type).

    No lit SKU entitled -> "Community" (the fail-closed default, e.g. an unlicensed tenant or
    the default empty-public-keys deployment); any lit SKU entitled -> "Licensed Add-ons"
    (the lit SKUs are discrete add-on apps -- there is no base-edition tier, so the label is
    deliberately conservative and never claims a tier it cannot prove). This is a
    read-only summary, NOT an authorization decision -- the gate stays ``is_entitled`` per SKU,
    so this label can never report "Enterprise" or grant access on a bare/any license.
    """
    return "Licensed Add-ons" if any(features.values()) else "Community"


def collect_license_status(session: Session, tenant_id: str) -> LicenseStatus:
    """Tenant-scoped, read-only entitlement + license summary. Key-leak-safe.

    Entitlement is decided ONLY by ``EntitlementService.is_entitled`` (the centralized
    gate); the ``AppLicense`` query here is a display summary, never an auth decision.
    """
    tenant_id = str(tenant_id or "").strip()
    if not tenant_id:
        # A blank tenant would let is_entitled() fall back to the "default" tenant (single
        # mode, resolve_license_scope) while the license summary queries tenant_id == "" -- a
        # misleading, inconsistent report. Refuse it rather than report a fallback tenant.
        raise ValueError("tenant_id is required (got blank/whitespace)")

    # is_entitled() scopes via tenant_id_var (resolve_license_scope); set it for the read.
    token = tenant_id_var.set(tenant_id)
    try:
        svc = EntitlementService(session)
        features = {key: svc.is_entitled(key) for key in _LIT_FEATURES}
    finally:
        tenant_id_var.reset(token)

    rows = (
        session.query(AppLicense)
        .filter(AppLicense.tenant_id == tenant_id)
        .order_by(AppLicense.app_name)
        .all()
    )
    licenses = [
        LicenseRowStatus(
            app_name=row.app_name,
            status=row.status,
            plan_type=row.plan_type,
            expires_at=row.expires_at.isoformat() if row.expires_at is not None else None,
            license_key=row.license_key,
        )
        for row in rows
    ]
    return LicenseStatus(
        tenant_id=tenant_id,
        features=features,
        edition=_derive_edition(features),
        licenses=licenses,
    )
