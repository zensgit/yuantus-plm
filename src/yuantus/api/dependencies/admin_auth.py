from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, Identity, get_current_identity
from yuantus.config import get_settings
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.models import Organization
from yuantus.security.auth.service import AuthService


def _get_org(db: Session, tenant_id: str, org_id: str) -> Organization:
    org = (
        db.query(Organization)
        .filter(Organization.tenant_id == tenant_id, Organization.id == org_id)
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return org


def require_superuser(
    identity: Identity | CurrentUser = Depends(get_current_identity),
) -> Identity | CurrentUser:
    if not identity.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")
    return identity


def require_platform_admin(identity: Identity = Depends(get_current_identity)) -> Identity:
    settings = get_settings()
    if not settings.PLATFORM_ADMIN_ENABLED:
        raise HTTPException(status_code=403, detail="Platform admin disabled")
    if not identity.is_superuser or identity.tenant_id != settings.PLATFORM_TENANT_ID:
        raise HTTPException(status_code=403, detail="Platform admin required")
    return identity


def require_org_admin(
    org_id: str,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_identity_db),
) -> Identity:
    _get_org(db, identity.tenant_id, org_id)
    if identity.is_superuser:
        return identity

    try:
        roles = AuthService(db).get_roles_for_user_org(
            tenant_id=identity.tenant_id, org_id=org_id, user_id=identity.user_id
        )
    except Exception:
        raise HTTPException(status_code=403, detail="Org admin required")
    if "admin" not in roles and "org_admin" not in roles:
        raise HTTPException(status_code=403, detail="Org admin required")
    return identity
