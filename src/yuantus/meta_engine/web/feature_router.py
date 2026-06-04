"""PLM Collaboration feature-entitlement affordance routes (PLM-COLLAB-P1-D).

The product-entry skeleton, not feature launch:
- ``GET /api/v1/features/{feature_key}`` -- the status the UI queries to decide
  whether to show an in-scenario upgrade entry. Available in base PLM too.
- ``POST /api/v1/features/{feature_key}/mock-activate`` -- a DEFAULT-OFF,
  superuser-only MOCK activation for demos/tests of the "click upgrade -> entitled"
  flow.

The ONLY entitlement check is ``EntitlementService.is_entitled`` -- no second
license check, no ``license_data`` read. The mock path is NEVER a production
authorization path: real authorization always goes through the P1-C signed
license import (or a vendor-server-signed license verified locally).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.admin_auth import require_superuser
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.app_framework.entitlement_service import EntitlementService
from yuantus.meta_engine.app_framework.license_scope import resolve_license_scope
from yuantus.meta_engine.app_framework.store_models import AppLicense

feature_router = APIRouter(prefix="/features", tags=["Feature Entitlement"])

_MOCK_FEATURE = "plm_collaboration_pro"
_MOCK_APP_NAME = "plm.collab"


@feature_router.get("/{feature_key}")
def feature_status(feature_key: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Entitlement status + upgrade affordance for the current tenant.

    ``entitled`` is the sole check (EntitlementService.is_entitled);
    ``upgrade.available`` is simply its negation -- the front end shows the
    in-scenario upgrade entry when not entitled.
    """
    try:
        entitled = EntitlementService(db).is_entitled(feature_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "feature_key": feature_key,
        "entitled": entitled,
        "upgrade": {"available": not entitled},
    }


def _require_mock_activation_enabled() -> None:
    """Default-off gate: 404 (looks absent) unless explicitly enabled.

    A FastAPI dependency so it runs BEFORE require_superuser -- when the mock path
    is disabled the endpoint returns 404 for everyone (including an unauthenticated
    caller), instead of leaking its existence via a 401/403 auth error first.
    """
    settings = get_settings()
    if not (settings.FEATURE_MOCK_ACTIVATION_ENABLED or settings.TEST_FAILPOINTS_ENABLED):
        raise HTTPException(status_code=404, detail="mock activation is not enabled")


def _require_mock_admin(
    _enabled: None = Depends(_require_mock_activation_enabled),
    identity: object = Depends(require_superuser),
) -> object:
    """Enforce the default-off gate FIRST, then superuser (dependency order matters)."""
    return identity


@feature_router.post("/{feature_key}/mock-activate")
def mock_activate(
    feature_key: str,
    db: Session = Depends(get_db),
    _identity: object = Depends(_require_mock_admin),
) -> Dict[str, Any]:
    """MOCK activation (demo/test only) -- NOT a production authorization path.

    Default-off (``_require_mock_admin`` 404s before the superuser check);
    superuser-only; only plm_collaboration_pro. Writes a tenant-scoped AppLicense
    marked ``license_data={"mock": true}`` (a marker, NOT an authorization source).
    Real authorization stays on P1-C.
    """
    if feature_key != _MOCK_FEATURE:
        raise HTTPException(
            status_code=400, detail=f"mock activation only supports {_MOCK_FEATURE!r}"
        )
    tenant_id, _org = resolve_license_scope()
    mock_key = f"mock:{tenant_id}:{_MOCK_APP_NAME}"
    lic = db.query(AppLicense).filter_by(license_key=mock_key).first()
    if lic is None:
        lic = AppLicense(id=uuid.uuid4().hex, license_key=mock_key)
        db.add(lic)
    lic.app_name = _MOCK_APP_NAME
    lic.tenant_id = tenant_id
    lic.plan_type = "Pro"
    lic.status = "Active"
    lic.expires_at = None
    lic.license_data = {"mock": True, "note": "P1-D demo/test mock; not a real license"}
    db.commit()
    return {"feature_key": feature_key, "entitled": True, "mock": True}
