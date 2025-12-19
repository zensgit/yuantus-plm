from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.requests import Request
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.security.auth.database import get_identity_db
from yuantus.security.auth.jwt import build_access_token_payload, encode_hs256
from yuantus.security.auth.service import AuthService
from yuantus.api.dependencies.auth import Identity, get_current_identity

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant id")
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)
    org_id: Optional[str] = Field(default=None, description="Optional default org id")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: str
    user_id: int


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_identity_db)) -> LoginResponse:
    settings = get_settings()
    service = AuthService(db)
    try:
        user = service.authenticate(
            tenant_id=req.tenant_id, username=req.username, password=req.password
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    if req.org_id:
        try:
            service.get_roles_for_user_org(
                tenant_id=req.tenant_id, org_id=req.org_id, user_id=user.id
            )
        except Exception:
            raise HTTPException(status_code=403, detail="Not a member of this org")

    payload = build_access_token_payload(
        user_id=user.id,
        tenant_id=req.tenant_id,
        org_id=req.org_id,
        ttl_seconds=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
    )
    token = encode_hs256(payload, secret=settings.JWT_SECRET_KEY)
    return LoginResponse(
        access_token=token,
        expires_in=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
        tenant_id=req.tenant_id,
        user_id=user.id,
    )


class MeResponse(BaseModel):
    tenant_id: str
    org_id: Optional[str] = None
    user_id: int
    username: str
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)


@router.get("/me", response_model=MeResponse)
def me(
    request: Request,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_identity_db),
) -> MeResponse:
    # If the request includes org context, expose roles; otherwise return identity only.
    roles: List[str] = []
    org_id: Optional[str] = None

    settings = get_settings()
    org_id = request.headers.get(settings.ORG_HEADER) or identity.org_id
    if org_id:
        service = AuthService(db)
        try:
            roles = service.get_roles_for_user_org(
                tenant_id=identity.tenant_id, org_id=str(org_id), user_id=identity.user_id
            )
        except Exception:
            roles = []

    if identity.is_superuser:
        roles = list({*roles, "admin", "superuser"})
    return MeResponse(
        tenant_id=identity.tenant_id,
        org_id=org_id,
        user_id=identity.user_id,
        username=identity.username or f"user-{identity.user_id}",
        email=identity.email,
        roles=roles,
    )


@router.get("/orgs", response_model=Dict[str, Any])
def list_orgs(
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_identity_db),
) -> Dict[str, Any]:
    service = AuthService(db)
    orgs = service.list_orgs_for_user(tenant_id=identity.tenant_id, user_id=identity.user_id)
    return {
        "tenant_id": identity.tenant_id,
        "user_id": identity.user_id,
        "orgs": [{"id": o.id, "name": o.name, "is_active": bool(o.is_active)} for o in orgs],
    }


class SwitchOrgRequest(BaseModel):
    org_id: str = Field(..., min_length=1, max_length=100, description="Target org id")


@router.post("/switch-org", response_model=LoginResponse)
def switch_org(
    req: SwitchOrgRequest,
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_identity_db),
) -> LoginResponse:
    settings = get_settings()
    service = AuthService(db)
    try:
        service.get_roles_for_user_org(
            tenant_id=identity.tenant_id, org_id=req.org_id, user_id=identity.user_id
        )
    except Exception:
        raise HTTPException(status_code=403, detail="Not a member of this org")

    payload = build_access_token_payload(
        user_id=identity.user_id,
        tenant_id=identity.tenant_id,
        org_id=req.org_id,
        ttl_seconds=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
    )
    token = encode_hs256(payload, secret=settings.JWT_SECRET_KEY)
    return LoginResponse(
        access_token=token,
        expires_in=settings.JWT_ACCESS_TOKEN_TTL_SECONDS,
        tenant_id=identity.tenant_id,
        user_id=identity.user_id,
    )
