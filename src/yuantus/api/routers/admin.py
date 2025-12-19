from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import Identity, get_current_identity
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.models import AuthCredential, AuthUser, Organization, OrgMembership, Tenant
from yuantus.security.auth.passwords import hash_password
from yuantus.security.auth.service import AuthService

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_superuser(identity: Identity = Depends(get_current_identity)) -> Identity:
    if not identity.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser required")
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


class TenantResponse(BaseModel):
    id: str
    name: Optional[str] = None
    is_active: bool
    created_at: datetime


class OrganizationCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, max_length=200)
    is_active: bool = Field(default=True)


class OrganizationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    is_active: Optional[bool] = None


class OrganizationResponse(BaseModel):
    id: str
    tenant_id: str
    name: Optional[str] = None
    is_active: bool
    created_at: datetime


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    email: Optional[str] = Field(default=None, max_length=200)
    is_superuser: bool = Field(default=False)
    user_id: Optional[int] = Field(default=None, description="Optional fixed user id (dev)")


class UserUpdateRequest(BaseModel):
    email: Optional[str] = Field(default=None, max_length=200)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    tenant_id: str
    username: str
    email: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)


class MembershipCreateRequest(BaseModel):
    user_id: Optional[int] = Field(default=None)
    username: Optional[str] = Field(default=None, min_length=1, max_length=100)
    roles: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)


class MembershipUpdateRequest(BaseModel):
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class MembershipResponse(BaseModel):
    tenant_id: str
    org_id: str
    user_id: int
    roles: List[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime


def _get_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _get_org(db: Session, tenant_id: str, org_id: str) -> Organization:
    org = (
        db.query(Organization)
        .filter(Organization.tenant_id == tenant_id, Organization.id == org_id)
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return org


def _get_user(db: Session, tenant_id: str, user_id: int) -> AuthUser:
    user = (
        db.query(AuthUser)
        .filter(AuthUser.tenant_id == tenant_id, AuthUser.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/tenant", response_model=TenantResponse)
def get_tenant_info(
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> TenantResponse:
    tenant = _get_tenant(db, identity.tenant_id)
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        is_active=bool(tenant.is_active),
        created_at=tenant.created_at,
    )


@router.get("/orgs", response_model=Dict[str, Any])
def list_orgs(
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    orgs = (
        db.query(Organization)
        .filter(Organization.tenant_id == identity.tenant_id)
        .order_by(Organization.created_at.asc())
        .all()
    )
    return {
        "tenant_id": identity.tenant_id,
        "items": [
            OrganizationResponse(
                id=o.id,
                tenant_id=o.tenant_id,
                name=o.name,
                is_active=bool(o.is_active),
                created_at=o.created_at,
            ).model_dump()
            for o in orgs
        ],
        "total": len(orgs),
    }


@router.post("/orgs", response_model=OrganizationResponse)
def create_org(
    req: OrganizationCreateRequest,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> OrganizationResponse:
    svc = AuthService(db)
    svc.ensure_tenant(identity.tenant_id, name=identity.tenant_id)

    existing = (
        db.query(Organization)
        .filter(Organization.tenant_id == identity.tenant_id, Organization.id == req.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Org already exists")

    org = Organization(
        id=req.id,
        tenant_id=identity.tenant_id,
        name=req.name or req.id,
        is_active=bool(req.is_active),
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrganizationResponse(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        is_active=bool(org.is_active),
        created_at=org.created_at,
    )


@router.get("/orgs/{org_id}", response_model=OrganizationResponse)
def get_org(
    org_id: str,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> OrganizationResponse:
    org = _get_org(db, identity.tenant_id, org_id)
    return OrganizationResponse(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        is_active=bool(org.is_active),
        created_at=org.created_at,
    )


@router.patch("/orgs/{org_id}", response_model=OrganizationResponse)
def update_org(
    org_id: str,
    req: OrganizationUpdateRequest,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> OrganizationResponse:
    org = _get_org(db, identity.tenant_id, org_id)
    if req.name is not None:
        org.name = req.name
    if req.is_active is not None:
        org.is_active = bool(req.is_active)
    db.add(org)
    db.commit()
    db.refresh(org)
    return OrganizationResponse(
        id=org.id,
        tenant_id=org.tenant_id,
        name=org.name,
        is_active=bool(org.is_active),
        created_at=org.created_at,
    )


@router.get("/users", response_model=Dict[str, Any])
def list_users(
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    users = (
        db.query(AuthUser)
        .filter(AuthUser.tenant_id == identity.tenant_id)
        .order_by(AuthUser.id.asc())
        .all()
    )
    return {
        "tenant_id": identity.tenant_id,
        "items": [
            UserResponse(
                id=u.id,
                tenant_id=u.tenant_id,
                username=u.username,
                email=u.email,
                is_active=bool(u.is_active),
                is_superuser=bool(u.is_superuser),
                created_at=u.created_at,
                updated_at=u.updated_at,
            ).model_dump()
            for u in users
        ],
        "total": len(users),
    }


@router.post("/users", response_model=UserResponse)
def create_user(
    req: UserCreateRequest,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> UserResponse:
    svc = AuthService(db)
    svc.ensure_tenant(identity.tenant_id, name=identity.tenant_id)

    try:
        user = svc.create_user(
            tenant_id=identity.tenant_id,
            username=req.username,
            password=req.password,
            email=req.email,
            is_superuser=bool(req.is_superuser),
            user_id=req.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e

    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        is_active=bool(user.is_active),
        is_superuser=bool(user.is_superuser),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    req: UserUpdateRequest,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> UserResponse:
    user = _get_user(db, identity.tenant_id, user_id)
    if req.email is not None:
        user.email = req.email
    if req.is_active is not None:
        user.is_active = bool(req.is_active)
    if req.is_superuser is not None:
        user.is_superuser = bool(req.is_superuser)
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        username=user.username,
        email=user.email,
        is_active=bool(user.is_active),
        is_superuser=bool(user.is_superuser),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/users/{user_id}/reset-password", response_model=Dict[str, Any])
def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    user = _get_user(db, identity.tenant_id, user_id)
    cred = db.get(AuthCredential, user.id)
    if not cred:
        cred = AuthCredential(user_id=user.id, password_hash=hash_password(req.password))
        db.add(cred)
    else:
        cred.password_hash = hash_password(req.password)
        db.add(cred)
    db.commit()
    return {"ok": True, "user_id": user.id}


@router.get("/orgs/{org_id}/members", response_model=Dict[str, Any])
def list_members(
    org_id: str,
    identity: Identity = Depends(require_org_admin),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    _get_org(db, identity.tenant_id, org_id)
    members = (
        db.query(OrgMembership)
        .filter(OrgMembership.tenant_id == identity.tenant_id, OrgMembership.org_id == org_id)
        .order_by(OrgMembership.created_at.asc())
        .all()
    )
    return {
        "tenant_id": identity.tenant_id,
        "org_id": org_id,
        "items": [
            MembershipResponse(
                tenant_id=m.tenant_id,
                org_id=m.org_id,
                user_id=m.user_id,
                roles=[str(r) for r in (m.roles or [])],
                is_active=bool(m.is_active),
                created_at=m.created_at,
            ).model_dump()
            for m in members
        ],
        "total": len(members),
    }


@router.post("/orgs/{org_id}/members", response_model=MembershipResponse)
def add_member(
    org_id: str,
    req: MembershipCreateRequest,
    identity: Identity = Depends(require_org_admin),
    db: Session = Depends(get_identity_db),
) -> MembershipResponse:
    _get_org(db, identity.tenant_id, org_id)

    target_user: Optional[AuthUser] = None
    if req.user_id is not None:
        target_user = _get_user(db, identity.tenant_id, int(req.user_id))
    elif req.username:
        target_user = (
            db.query(AuthUser)
            .filter(AuthUser.tenant_id == identity.tenant_id, AuthUser.username == req.username)
            .first()
        )
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        raise HTTPException(status_code=400, detail="user_id or username required")

    svc = AuthService(db)
    membership = svc.add_membership(
        tenant_id=identity.tenant_id,
        org_id=org_id,
        user_id=target_user.id,
        roles=[str(r) for r in (req.roles or [])],
    )
    membership.is_active = bool(req.is_active)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return MembershipResponse(
        tenant_id=membership.tenant_id,
        org_id=membership.org_id,
        user_id=membership.user_id,
        roles=[str(r) for r in (membership.roles or [])],
        is_active=bool(membership.is_active),
        created_at=membership.created_at,
    )


@router.patch("/orgs/{org_id}/members/{user_id}", response_model=MembershipResponse)
def update_member(
    org_id: str,
    user_id: int,
    req: MembershipUpdateRequest,
    identity: Identity = Depends(require_org_admin),
    db: Session = Depends(get_identity_db),
) -> MembershipResponse:
    _get_org(db, identity.tenant_id, org_id)
    _get_user(db, identity.tenant_id, user_id)

    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.tenant_id == identity.tenant_id,
            OrgMembership.org_id == org_id,
            OrgMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    if req.roles is not None:
        membership.roles = [str(r) for r in req.roles]
    if req.is_active is not None:
        membership.is_active = bool(req.is_active)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return MembershipResponse(
        tenant_id=membership.tenant_id,
        org_id=membership.org_id,
        user_id=membership.user_id,
        roles=[str(r) for r in (membership.roles or [])],
        is_active=bool(membership.is_active),
        created_at=membership.created_at,
    )
