from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import Identity, get_current_identity
from yuantus.config import get_settings
from yuantus.database import SessionLocal as GlobalSessionLocal
from yuantus.database import get_db
from yuantus.database import get_sessionmaker_for_scope, get_sessionmaker_for_tenant
from yuantus.models.audit import AuditLog
from yuantus.security.audit_retention import get_last_prune_ts, prune_audit_logs
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.models import (
    AuthCredential,
    AuthUser,
    Organization,
    OrgMembership,
    Tenant,
    TenantQuota,
)
from yuantus.security.auth.passwords import hash_password
from yuantus.security.auth.quota_service import QuotaService
from yuantus.security.auth.service import AuthService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.models import (
    Relationship,
    RelationshipType,
    get_relationship_write_block_stats,
    simulate_relationship_write_block,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_superuser(identity: Identity = Depends(get_current_identity)) -> Identity:
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


class TenantResponse(BaseModel):
    id: str
    name: Optional[str] = None
    is_active: bool
    created_at: datetime


class TenantCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: Optional[str] = Field(default=None, max_length=200)
    is_active: bool = Field(default=True)
    create_default_org: bool = Field(default=True)
    default_org_id: str = Field(default="org-1", min_length=1, max_length=64)
    admin_username: Optional[str] = Field(default=None, max_length=100)
    admin_password: Optional[str] = Field(default=None, max_length=200)
    admin_email: Optional[str] = Field(default=None, max_length=200)
    admin_user_id: Optional[int] = Field(default=None, description="Optional fixed user id (dev)")


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    is_active: Optional[bool] = None


class TenantQuotaData(BaseModel):
    max_users: Optional[int] = Field(default=None, ge=0)
    max_orgs: Optional[int] = Field(default=None, ge=0)
    max_files: Optional[int] = Field(default=None, ge=0)
    max_storage_bytes: Optional[int] = Field(default=None, ge=0)
    max_active_jobs: Optional[int] = Field(default=None, ge=0)
    max_processing_jobs: Optional[int] = Field(default=None, ge=0)


class TenantQuotaResponse(BaseModel):
    tenant_id: str
    mode: str
    quota: TenantQuotaData
    usage: Dict[str, Optional[int]]
    updated_at: Optional[datetime] = None


class TenantQuotaListResponse(BaseModel):
    items: List[TenantQuotaResponse]


class AuditRetentionResponse(BaseModel):
    tenant_id: str
    retention_days: int
    retention_max_rows: int
    prune_interval_seconds: int
    last_prune_ts: float


class AuditPruneResponse(BaseModel):
    tenant_id: str
    retention_days: int
    retention_max_rows: int
    deleted: int


class RelationshipWriteBlockResponse(BaseModel):
    window_seconds: int
    blocked: int
    recent: List[float]
    last_blocked_at: Optional[float] = None
    warn_threshold: Optional[int] = None
    warn: bool = False


class RelationshipLegacyTypeStat(BaseModel):
    id: str
    name: Optional[str] = None
    label: Optional[str] = None
    item_type_id: str
    relationship_count: int
    relationship_item_count: int


class RelationshipLegacyUsageEntry(BaseModel):
    tenant_id: str
    org_id: Optional[str] = None
    relationship_type_count: int
    relationship_row_count: int
    relationship_item_type_count: int
    relationship_item_count: int
    meta_relationships_missing: bool = False
    meta_relationship_types_missing: bool = False
    types: List[RelationshipLegacyTypeStat] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class RelationshipLegacyUsageResponse(BaseModel):
    items: List[RelationshipLegacyUsageEntry]
    total: int


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


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    tenant_id: Optional[str] = None
    org_id: Optional[str] = None
    user_id: Optional[int] = None
    method: str
    path: str
    status_code: int
    duration_ms: int
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    error: Optional[str] = None


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


def _open_meta_session(tenant_id: str, org_id: Optional[str]) -> Optional[Session]:
    settings = get_settings()
    if settings.TENANCY_MODE == "db-per-tenant-org":
        if not org_id:
            return None
        SessionLocal = get_sessionmaker_for_scope(tenant_id, org_id)
    elif settings.TENANCY_MODE == "db-per-tenant":
        SessionLocal = get_sessionmaker_for_tenant(tenant_id)
    else:
        SessionLocal = GlobalSessionLocal
    return SessionLocal()


def _resolve_audit_tenant(identity: Identity, tenant_id: Optional[str]) -> str:
    if tenant_id and tenant_id != identity.tenant_id:
        require_platform_admin(identity)
        return tenant_id
    return tenant_id or identity.tenant_id


def _build_relationship_legacy_usage(
    session: Session,
    *,
    tenant_id: str,
    org_id: Optional[str],
    include_details: bool,
) -> RelationshipLegacyUsageEntry:
    bind = session.get_bind()
    inspector = inspect(bind)
    has_relationships = inspector.has_table(Relationship.__tablename__)
    has_relationship_types = inspector.has_table(RelationshipType.__tablename__)

    rel_types: List[RelationshipType] = []
    if has_relationship_types:
        rel_types = (
            session.query(RelationshipType)
            .order_by(RelationshipType.id.asc())
            .all()
        )

    relationship_type_count = len(rel_types)
    relationship_row_count = (
        session.query(Relationship).count() if has_relationships else 0
    )

    rel_item_type_ids = [
        row[0]
        for row in session.query(ItemType.id)
        .filter(ItemType.is_relationship.is_(True))
        .all()
    ]
    relationship_item_type_count = len(rel_item_type_ids)
    relationship_item_count = (
        session.query(Item)
        .filter(Item.item_type_id.in_(rel_item_type_ids), Item.is_current.is_(True))
        .count()
        if rel_item_type_ids
        else 0
    )

    types: List[RelationshipLegacyTypeStat] = []
    if include_details and rel_types:
        for rel_type in rel_types:
            item_type_id = rel_type.name or rel_type.id
            rel_count = (
                session.query(Relationship)
                .filter(Relationship.relationship_type_id == rel_type.id)
                .count()
                if has_relationships
                else 0
            )
            item_count = (
                session.query(Item)
                .filter(
                    Item.item_type_id == item_type_id,
                    Item.is_current.is_(True),
                )
                .count()
            )
            types.append(
                RelationshipLegacyTypeStat(
                    id=rel_type.id,
                    name=rel_type.name,
                    label=rel_type.label,
                    item_type_id=item_type_id,
                    relationship_count=int(rel_count),
                    relationship_item_count=int(item_count),
                )
            )

    warnings: List[str] = []
    if relationship_type_count:
        warnings.append("legacy_relationship_types_present")
    if relationship_row_count:
        warnings.append("legacy_relationship_rows_present")
    if relationship_item_count and not relationship_type_count:
        warnings.append("relationship_items_without_relationship_types")
    if not has_relationships:
        warnings.append("meta_relationships_table_missing")
    if not has_relationship_types:
        warnings.append("meta_relationship_types_table_missing")

    return RelationshipLegacyUsageEntry(
        tenant_id=tenant_id,
        org_id=org_id,
        relationship_type_count=int(relationship_type_count),
        relationship_row_count=int(relationship_row_count),
        relationship_item_type_count=int(relationship_item_type_count),
        relationship_item_count=int(relationship_item_count),
        meta_relationships_missing=not has_relationships,
        meta_relationship_types_missing=not has_relationship_types,
        types=types,
        warnings=warnings,
    )


def _apply_quota_limits(
    quota_service: QuotaService,
    tenant_id: str,
    deltas: Dict[str, int],
    response: Optional[Response],
) -> None:
    decisions = quota_service.evaluate(tenant_id, deltas=deltas)
    if not decisions:
        return
    if quota_service.mode == "soft":
        if response is not None:
            response.headers["X-Quota-Warning"] = QuotaService.build_warning(decisions)
        return
    detail = {
        "code": "QUOTA_EXCEEDED",
        **QuotaService.build_error_payload(tenant_id, decisions),
    }
    raise HTTPException(status_code=429, detail=detail)


def _serialize_quota(quota: Optional[TenantQuota]) -> TenantQuotaData:
    if not quota:
        return TenantQuotaData()
    return TenantQuotaData(
        max_users=quota.max_users,
        max_orgs=quota.max_orgs,
        max_files=quota.max_files,
        max_storage_bytes=quota.max_storage_bytes,
        max_active_jobs=quota.max_active_jobs,
        max_processing_jobs=quota.max_processing_jobs,
    )


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


@router.get("/tenants", response_model=Dict[str, Any])
def list_tenants(
    identity: Identity = Depends(require_platform_admin),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    tenants = db.query(Tenant).order_by(Tenant.created_at.asc()).all()
    return {
        "items": [
            TenantResponse(
                id=t.id,
                name=t.name,
                is_active=bool(t.is_active),
                created_at=t.created_at,
            ).model_dump()
            for t in tenants
        ],
        "total": len(tenants),
    }


@router.get("/tenants/quotas", response_model=TenantQuotaListResponse)
def list_tenant_quotas(
    org_id: Optional[str] = Query(None, description="Org id for meta usage in db-per-tenant-org"),
    identity: Identity = Depends(require_platform_admin),
    identity_db: Session = Depends(get_identity_db),
) -> TenantQuotaListResponse:
    tenants = identity_db.query(Tenant).order_by(Tenant.id.asc()).all()
    items: List[TenantQuotaResponse] = []
    for tenant in tenants:
        quota_service = QuotaService(identity_db)
        quota = quota_service.get_quota(tenant.id)
        meta_session = _open_meta_session(tenant.id, org_id)
        try:
            if meta_session is not None:
                quota_service = QuotaService(identity_db, meta_db=meta_session)
            usage = quota_service.get_usage(tenant.id)
        finally:
            if meta_session is not None:
                meta_session.close()
        items.append(
            TenantQuotaResponse(
                tenant_id=tenant.id,
                mode=quota_service.mode,
                quota=_serialize_quota(quota),
                usage=usage.to_dict(),
                updated_at=quota.updated_at if quota else None,
            )
        )
    return TenantQuotaListResponse(items=items)


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str,
    identity: Identity = Depends(require_platform_admin),
    db: Session = Depends(get_identity_db),
) -> TenantResponse:
    tenant = _get_tenant(db, tenant_id)
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        is_active=bool(tenant.is_active),
        created_at=tenant.created_at,
    )


@router.post("/tenants", response_model=TenantResponse)
def create_tenant(
    req: TenantCreateRequest,
    identity: Identity = Depends(require_platform_admin),
    db: Session = Depends(get_identity_db),
) -> TenantResponse:
    existing = db.get(Tenant, req.id)
    if existing:
        raise HTTPException(status_code=409, detail="Tenant already exists")

    tenant = Tenant(
        id=req.id,
        name=req.name or req.id,
        is_active=bool(req.is_active),
    )
    db.add(tenant)

    if (req.admin_username and not req.admin_password) or (
        req.admin_password and not req.admin_username
    ):
        raise HTTPException(status_code=400, detail="admin_username and admin_password required")

    org: Optional[Organization] = None
    if req.create_default_org or req.admin_username:
        org = (
            db.query(Organization)
            .filter(Organization.tenant_id == req.id, Organization.id == req.default_org_id)
            .first()
        )
        if not org:
            org = Organization(
                id=req.default_org_id,
                tenant_id=req.id,
                name=req.default_org_id,
                is_active=True,
            )
            db.add(org)

    if req.admin_username:
        svc = AuthService(db)
        try:
            admin_user = svc.create_user(
                tenant_id=req.id,
                username=req.admin_username,
                password=req.admin_password or "",
                email=req.admin_email,
                is_superuser=True,
                user_id=req.admin_user_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

        if org:
            svc.add_membership(
                tenant_id=req.id,
                org_id=org.id,
                user_id=admin_user.id,
                roles=["admin"],
            )

    db.commit()
    db.refresh(tenant)
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        is_active=bool(tenant.is_active),
        created_at=tenant.created_at,
    )


@router.patch("/tenants/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: str,
    req: TenantUpdateRequest,
    identity: Identity = Depends(require_platform_admin),
    db: Session = Depends(get_identity_db),
) -> TenantResponse:
    tenant = _get_tenant(db, tenant_id)
    if req.name is not None:
        tenant.name = req.name
    if req.is_active is not None:
        tenant.is_active = bool(req.is_active)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
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
    response: Response,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> OrganizationResponse:
    svc = AuthService(db)
    svc.ensure_tenant(identity.tenant_id, name=identity.tenant_id)

    quota_service = QuotaService(db)
    _apply_quota_limits(quota_service, identity.tenant_id, {"orgs": 1}, response)

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


@router.get("/tenants/{tenant_id}/orgs", response_model=Dict[str, Any])
def list_orgs_for_tenant(
    tenant_id: str,
    identity: Identity = Depends(require_platform_admin),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    orgs = (
        db.query(Organization)
        .filter(Organization.tenant_id == tenant_id)
        .order_by(Organization.created_at.asc())
        .all()
    )
    return {
        "tenant_id": tenant_id,
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


@router.post("/tenants/{tenant_id}/orgs", response_model=OrganizationResponse)
def create_org_for_tenant(
    tenant_id: str,
    req: OrganizationCreateRequest,
    response: Response,
    identity: Identity = Depends(require_platform_admin),
    db: Session = Depends(get_identity_db),
) -> OrganizationResponse:
    svc = AuthService(db)
    svc.ensure_tenant(tenant_id, name=tenant_id)

    quota_service = QuotaService(db)
    _apply_quota_limits(quota_service, tenant_id, {"orgs": 1}, response)

    existing = (
        db.query(Organization)
        .filter(Organization.tenant_id == tenant_id, Organization.id == req.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Org already exists")

    org = Organization(
        id=req.id,
        tenant_id=tenant_id,
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
    response: Response,
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> UserResponse:
    svc = AuthService(db)
    svc.ensure_tenant(identity.tenant_id, name=identity.tenant_id)

    quota_service = QuotaService(db)
    _apply_quota_limits(quota_service, identity.tenant_id, {"users": 1}, response)

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


@router.get("/quota", response_model=TenantQuotaResponse)
def get_quota(
    identity: Identity = Depends(require_superuser),
    identity_db: Session = Depends(get_identity_db),
    meta_db: Session = Depends(get_db),
) -> TenantQuotaResponse:
    quota_service = QuotaService(identity_db, meta_db=meta_db)
    quota = quota_service.get_quota(identity.tenant_id)
    usage = quota_service.get_usage(identity.tenant_id)
    return TenantQuotaResponse(
        tenant_id=identity.tenant_id,
        mode=quota_service.mode,
        quota=_serialize_quota(quota),
        usage=usage.to_dict(),
        updated_at=quota.updated_at if quota else None,
    )


@router.put("/quota", response_model=TenantQuotaResponse)
def update_quota(
    req: TenantQuotaData,
    identity: Identity = Depends(require_superuser),
    identity_db: Session = Depends(get_identity_db),
    meta_db: Session = Depends(get_db),
) -> TenantQuotaResponse:
    updates = req.model_dump(exclude_unset=True)
    quota_service = QuotaService(identity_db, meta_db=meta_db)
    quota = quota_service.upsert_quota(identity.tenant_id, updates=updates)
    identity_db.commit()
    usage = quota_service.get_usage(identity.tenant_id)
    return TenantQuotaResponse(
        tenant_id=identity.tenant_id,
        mode=quota_service.mode,
        quota=_serialize_quota(quota),
        usage=usage.to_dict(),
        updated_at=quota.updated_at if quota else None,
    )


@router.get("/tenants/{tenant_id}/quota", response_model=TenantQuotaResponse)
def get_quota_for_tenant(
    tenant_id: str,
    org_id: Optional[str] = Query(None, description="Org id for meta usage in db-per-tenant-org"),
    identity: Identity = Depends(require_platform_admin),
    identity_db: Session = Depends(get_identity_db),
) -> TenantQuotaResponse:
    quota_service = QuotaService(identity_db)
    quota = quota_service.get_quota(tenant_id)
    meta_session = _open_meta_session(tenant_id, org_id)
    try:
        if meta_session is not None:
            quota_service = QuotaService(identity_db, meta_db=meta_session)
        usage = quota_service.get_usage(tenant_id)
    finally:
        if meta_session is not None:
            meta_session.close()
    return TenantQuotaResponse(
        tenant_id=tenant_id,
        mode=quota_service.mode,
        quota=_serialize_quota(quota),
        usage=usage.to_dict(),
        updated_at=quota.updated_at if quota else None,
    )


@router.put("/tenants/{tenant_id}/quota", response_model=TenantQuotaResponse)
def update_quota_for_tenant(
    tenant_id: str,
    req: TenantQuotaData,
    org_id: Optional[str] = Query(None, description="Org id for meta usage in db-per-tenant-org"),
    identity: Identity = Depends(require_platform_admin),
    identity_db: Session = Depends(get_identity_db),
) -> TenantQuotaResponse:
    updates = req.model_dump(exclude_unset=True)
    quota_service = QuotaService(identity_db)
    quota = quota_service.upsert_quota(tenant_id, updates=updates)
    identity_db.commit()
    meta_session = _open_meta_session(tenant_id, org_id)
    try:
        if meta_session is not None:
            quota_service = QuotaService(identity_db, meta_db=meta_session)
        usage = quota_service.get_usage(tenant_id)
    finally:
        if meta_session is not None:
            meta_session.close()
    return TenantQuotaResponse(
        tenant_id=tenant_id,
        mode=quota_service.mode,
        quota=_serialize_quota(quota),
        usage=usage.to_dict(),
        updated_at=quota.updated_at if quota else None,
    )


@router.get("/audit", response_model=Dict[str, Any])
def list_audit_logs(
    tenant_id: Optional[str] = Query(None, description="Tenant id filter (defaults to current)"),
    org_id: Optional[str] = Query(None, description="Organization id filter"),
    user_id: Optional[int] = Query(None, description="User id filter"),
    path: Optional[str] = Query(None, description="Path contains filter"),
    method: Optional[str] = Query(None, description="HTTP method filter"),
    status_code: Optional[int] = Query(None, description="HTTP status code filter"),
    since: Optional[datetime] = Query(None, description="Created >= timestamp"),
    until: Optional[datetime] = Query(None, description="Created < timestamp"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    if tenant_id and tenant_id != identity.tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant audit access is not allowed")

    tenant_filter = tenant_id or identity.tenant_id
    query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_filter)

    if org_id:
        query = query.filter(AuditLog.org_id == org_id)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if path:
        query = query.filter(AuditLog.path.contains(path))
    if method:
        query = query.filter(AuditLog.method == method.strip().upper())
    if status_code is not None:
        query = query.filter(AuditLog.status_code == status_code)
    if since:
        query = query.filter(AuditLog.created_at >= since)
    if until:
        query = query.filter(AuditLog.created_at < until)

    total = query.count()
    rows = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "tenant_id": tenant_filter,
        "items": [AuditLogResponse.model_validate(r).model_dump() for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/audit/retention", response_model=AuditRetentionResponse)
def get_audit_retention(
    tenant_id: Optional[str] = Query(
        None, description="Tenant id (defaults to current; platform admin can target others)"
    ),
    identity: Identity = Depends(require_superuser),
) -> AuditRetentionResponse:
    settings = get_settings()
    target_tenant = _resolve_audit_tenant(identity, tenant_id)
    return AuditRetentionResponse(
        tenant_id=target_tenant,
        retention_days=int(settings.AUDIT_RETENTION_DAYS or 0),
        retention_max_rows=int(settings.AUDIT_RETENTION_MAX_ROWS or 0),
        prune_interval_seconds=int(settings.AUDIT_RETENTION_PRUNE_INTERVAL_SECONDS or 0),
        last_prune_ts=get_last_prune_ts(target_tenant),
    )


@router.post("/audit/prune", response_model=AuditPruneResponse)
def prune_audit(
    tenant_id: Optional[str] = Query(
        None, description="Tenant id (defaults to current; platform admin can target others)"
    ),
    identity: Identity = Depends(require_superuser),
    db: Session = Depends(get_identity_db),
) -> AuditPruneResponse:
    settings = get_settings()
    target_tenant = _resolve_audit_tenant(identity, tenant_id)
    deleted = prune_audit_logs(
        db,
        retention_days=int(settings.AUDIT_RETENTION_DAYS or 0),
        retention_max_rows=int(settings.AUDIT_RETENTION_MAX_ROWS or 0),
        tenant_id=target_tenant,
    )
    return AuditPruneResponse(
        tenant_id=target_tenant,
        retention_days=int(settings.AUDIT_RETENTION_DAYS or 0),
        retention_max_rows=int(settings.AUDIT_RETENTION_MAX_ROWS or 0),
        deleted=int(deleted),
    )


@router.get("/relationship-types/legacy-usage", response_model=RelationshipLegacyUsageResponse)
def get_relationship_legacy_usage(
    tenant_id: Optional[str] = Query(
        None, description="Target tenant (platform admin can target others)"
    ),
    org_id: Optional[str] = Query(
        None, description="Org id (required for db-per-tenant-org)"
    ),
    include_details: bool = Query(
        False, description="Include per-RelationshipType breakdown"
    ),
    identity: Identity = Depends(require_superuser),
) -> RelationshipLegacyUsageResponse:
    settings = get_settings()
    target_tenant = _resolve_audit_tenant(identity, tenant_id)

    target_org = org_id or identity.org_id
    if settings.TENANCY_MODE == "db-per-tenant-org" and not target_org:
        raise HTTPException(status_code=400, detail="org_id required")

    session = _open_meta_session(target_tenant, target_org)
    if session is None:
        raise HTTPException(status_code=404, detail="Meta DB not available for scope")

    try:
        entry = _build_relationship_legacy_usage(
            session,
            tenant_id=target_tenant,
            org_id=target_org,
            include_details=include_details,
        )
    finally:
        session.close()

    return RelationshipLegacyUsageResponse(items=[entry], total=1)


@router.get("/relationship-writes", response_model=RelationshipWriteBlockResponse)
def get_relationship_write_blocks(
    window_seconds: int = Query(86400, ge=60, le=604800),
    recent_limit: int = Query(20, ge=0, le=200),
    warn_threshold: int = Query(
        10, ge=0, le=100000, description="Warn when blocked >= threshold; 0 disables"
    ),
    identity: Identity = Depends(require_platform_admin),
) -> RelationshipWriteBlockResponse:
    stats = get_relationship_write_block_stats(
        window_seconds=window_seconds, recent_limit=recent_limit
    )
    stats["warn_threshold"] = warn_threshold
    stats["warn"] = bool(warn_threshold and stats["blocked"] >= warn_threshold)
    return RelationshipWriteBlockResponse(**stats)


@router.post("/relationship-writes/simulate", response_model=RelationshipWriteBlockResponse)
def simulate_relationship_write(
    operation: str = Query("insert", pattern="^(insert|update|delete)$"),
    window_seconds: int = Query(86400, ge=60, le=604800),
    recent_limit: int = Query(20, ge=0, le=200),
    warn_threshold: int = Query(
        10, ge=0, le=100000, description="Warn when blocked >= threshold; 0 disables"
    ),
    identity: Identity = Depends(require_platform_admin),
) -> RelationshipWriteBlockResponse:
    settings = get_settings()
    if settings.ENVIRONMENT not in {"dev", "test"} and not settings.RELATIONSHIP_SIMULATE_ENABLED:
        raise HTTPException(status_code=404, detail="Not Found")
    try:
        simulate_relationship_write_block(operation=operation)
    except Exception:
        pass
    stats = get_relationship_write_block_stats(
        window_seconds=window_seconds, recent_limit=recent_limit
    )
    stats["warn_threshold"] = warn_threshold
    stats["warn"] = bool(warn_threshold and stats["blocked"] >= warn_threshold)
    return RelationshipWriteBlockResponse(**stats)
