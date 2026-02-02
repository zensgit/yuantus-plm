from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from fastapi import Depends, HTTPException
from starlette.requests import Request
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.context import user_id_var
from yuantus.database import get_db
from yuantus.models.user import User as LocalUser
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.jwt import JWTError, decode_hs256
from yuantus.security.auth.models import AuthUser
from yuantus.security.auth.service import AuthService
from yuantus.security.rbac.models import RBACRole, RBACUser


@dataclass(frozen=True)
class Identity:
    user_id: int
    tenant_id: str
    org_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    is_superuser: bool = False


@dataclass(frozen=True)
class CurrentUser:
    id: int
    tenant_id: str
    org_id: str
    username: str
    email: Optional[str]
    roles: List[str]
    is_superuser: bool = False


def _get_bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _auth_mode() -> str:
    mode = (get_settings().AUTH_MODE or "optional").strip().lower()
    if mode not in {"disabled", "optional", "required"}:
        return "optional"
    return mode


def get_current_identity(
    request: Request,
    identity_db: Session = Depends(get_identity_db),
) -> Identity:
    settings = get_settings()
    mode = _auth_mode()
    if mode == "disabled":
        raise HTTPException(status_code=400, detail="Auth is disabled")

    token = _get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        payload = decode_hs256(
            token, secret=settings.JWT_SECRET_KEY, leeway_seconds=settings.AUTH_LEEWAY_SECONDS
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    tenant_id = payload.get("tenant_id")
    sub = payload.get("sub")
    if not tenant_id or not sub:
        raise HTTPException(status_code=401, detail="Invalid token claims")

    tenant_header = request.headers.get(settings.TENANT_HEADER)
    if tenant_header and str(tenant_header) != str(tenant_id):
        raise HTTPException(status_code=401, detail="Tenant mismatch")

    try:
        user_id = int(sub)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid sub claim") from e

    user: Optional[AuthUser] = (
        identity_db.query(AuthUser)
        .filter(AuthUser.id == user_id, AuthUser.tenant_id == str(tenant_id))
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return Identity(
        user_id=user.id,
        tenant_id=str(tenant_id),
        org_id=payload.get("org_id"),
        username=user.username,
        email=user.email,
        is_superuser=bool(user.is_superuser),
    )


def _ensure_local_user(db: Session, identity: Identity) -> None:
    existing = db.get(LocalUser, identity.user_id)
    if not existing:
        fallback_username = identity.username or f"user-{identity.user_id}"
        existing_by_username = (
            db.query(LocalUser).filter(LocalUser.username == fallback_username).first()
        )
        if existing_by_username:
            changed = False
            if identity.email is not None and existing_by_username.email != identity.email:
                existing_by_username.email = identity.email
                changed = True
            if not existing_by_username.is_active:
                existing_by_username.is_active = True
                changed = True
            if changed:
                db.add(existing_by_username)
                db.flush()
            return

        db.add(
            LocalUser(
                id=identity.user_id,
                username=fallback_username,
                email=identity.email,
                is_active=True,
            )
        )
        db.flush()
        return

    changed = False
    if identity.username and existing.username != identity.username:
        existing.username = identity.username
        changed = True
    if identity.email is not None and existing.email != identity.email:
        existing.email = identity.email
        changed = True
    if changed:
        db.add(existing)
        db.flush()


def _ensure_rbac_user(db: Session, identity: Identity) -> None:
    existing = db.get(RBACUser, identity.user_id)
    if not existing:
        fallback_username = identity.username or f"user-{identity.user_id}"
        existing_by_username = (
            db.query(RBACUser).filter(RBACUser.username == fallback_username).first()
        )
        if existing_by_username:
            changed = False
            if identity.email is not None and existing_by_username.email != identity.email:
                existing_by_username.email = identity.email
                changed = True
            if bool(existing_by_username.is_superuser) != bool(identity.is_superuser):
                existing_by_username.is_superuser = identity.is_superuser
                changed = True
            if not existing_by_username.is_active:
                existing_by_username.is_active = True
                changed = True
            if changed:
                db.add(existing_by_username)
                db.flush()
            return

        db.add(
            RBACUser(
                id=identity.user_id,
                user_id=identity.user_id,
                username=fallback_username,
                email=identity.email,
                is_active=True,
                is_superuser=identity.is_superuser,
            )
        )
        db.flush()
        return

    changed = False
    if identity.username and existing.username != identity.username:
        existing.username = identity.username
        changed = True
    if identity.email is not None and existing.email != identity.email:
        existing.email = identity.email
        changed = True
    if bool(existing.is_superuser) != bool(identity.is_superuser):
        existing.is_superuser = identity.is_superuser
        changed = True
    if changed:
        db.add(existing)
        db.flush()


def get_current_user_optional(
    request: Request,
    identity_db: Session = Depends(get_identity_db),
    db: Session = Depends(get_db),
) -> Optional[CurrentUser]:
    settings = get_settings()
    mode = _auth_mode()

    token = _get_bearer_token(request)
    if not token:
        if mode == "required":
            raise HTTPException(status_code=401, detail="Missing bearer token")
        return None

    identity = get_current_identity(request, identity_db=identity_db)

    # Tenant header must match token claim (when provided).
    tenant_header = request.headers.get(settings.TENANT_HEADER)
    if tenant_header and tenant_header != identity.tenant_id:
        raise HTTPException(status_code=401, detail="Tenant mismatch")

    # Resolve org from header or token default
    org_id = request.headers.get(settings.ORG_HEADER) or identity.org_id
    if not org_id:
        raise HTTPException(status_code=400, detail="Missing org id")

    auth_service = AuthService(identity_db)
    try:
        roles = auth_service.get_roles_for_user_org(
            tenant_id=identity.tenant_id, org_id=str(org_id), user_id=identity.user_id
        )
    except Exception:
        raise HTTPException(status_code=403, detail="Not a member of this org")

    if identity.is_superuser:
        roles = list({*roles, "admin", "superuser"})

    _ensure_local_user(db, identity)
    _ensure_rbac_user(db, identity)

    # Ensure RBAC role records exist (org DB) and assign to RBACUser.
    rbac_user = db.get(RBACUser, identity.user_id)
    if rbac_user is None and identity.username:
        rbac_user = db.query(RBACUser).filter_by(username=identity.username).first()
    if rbac_user is None:
        raise HTTPException(status_code=401, detail="RBAC user not found")
    existing_role_names = {r.name for r in (rbac_user.roles or [])}
    for role_name in roles:
        role_name = str(role_name)
        role = db.query(RBACRole).filter_by(name=role_name).first()
        if not role:
            role = RBACRole(
                name=role_name,
                display_name=role_name,
                description="Auto-provisioned role",
                is_system=False,
                is_active=True,
            )
            db.add(role)
            db.flush()
        if role.name not in existing_role_names:
            rbac_user.roles.append(role)
            existing_role_names.add(role.name)
    db.add(rbac_user)
    db.flush()

    user_id_var.set(str(identity.user_id))

    return CurrentUser(
        id=identity.user_id,
        tenant_id=identity.tenant_id,
        org_id=str(org_id),
        username=identity.username or f"user-{identity.user_id}",
        email=identity.email,
        roles=roles,
        is_superuser=identity.is_superuser,
    )


def get_current_user(
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
) -> CurrentUser:
    if user is None:
        mode = _auth_mode()
        if mode == "disabled":
            raise HTTPException(status_code=400, detail="Auth is disabled")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def get_current_user_id(user: CurrentUser = Depends(get_current_user)) -> int:
    return user.id


def get_current_user_id_optional(
    user: Optional[CurrentUser] = Depends(get_current_user_optional),
) -> int:
    if user is None:
        return 1
    return user.id
