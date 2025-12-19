from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from yuantus.security.auth.models import (
    AuthCredential,
    AuthUser,
    Organization,
    OrgMembership,
    Tenant,
)
from yuantus.security.auth.passwords import hash_password, verify_password


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def ensure_tenant(self, tenant_id: str, *, name: Optional[str] = None) -> Tenant:
        tenant = self.session.get(Tenant, tenant_id)
        if tenant:
            return tenant
        tenant = Tenant(id=tenant_id, name=name or tenant_id, is_active=True)
        self.session.add(tenant)
        self.session.flush()
        return tenant

    def ensure_org(self, tenant_id: str, org_id: str, *, name: Optional[str] = None) -> Organization:
        org = self.session.get(Organization, org_id)
        if org:
            return org
        org = Organization(id=org_id, tenant_id=tenant_id, name=name or org_id, is_active=True)
        self.session.add(org)
        self.session.flush()
        return org

    def create_user(
        self,
        *,
        tenant_id: str,
        username: str,
        password: str,
        email: Optional[str] = None,
        is_superuser: bool = False,
        user_id: Optional[int] = None,
    ) -> AuthUser:
        user = (
            self.session.query(AuthUser)
            .filter(AuthUser.tenant_id == tenant_id, AuthUser.username == username)
            .first()
        )
        if user:
            raise ValueError("User already exists")

        user = AuthUser(
            id=user_id,
            tenant_id=tenant_id,
            username=username,
            email=email,
            is_active=True,
            is_superuser=is_superuser,
        )
        self.session.add(user)
        self.session.flush()

        cred = AuthCredential(user_id=user.id, password_hash=hash_password(password))
        self.session.add(cred)
        self.session.flush()
        return user

    def set_password(self, *, tenant_id: str, username: str, password: str) -> None:
        user = (
            self.session.query(AuthUser)
            .filter(AuthUser.tenant_id == tenant_id, AuthUser.username == username)
            .first()
        )
        if not user:
            raise ValueError("User not found")

        cred = self.session.get(AuthCredential, user.id)
        if not cred:
            cred = AuthCredential(user_id=user.id, password_hash=hash_password(password))
            self.session.add(cred)
        else:
            cred.password_hash = hash_password(password)
        self.session.flush()

    def authenticate(self, *, tenant_id: str, username: str, password: str) -> AuthUser:
        user = (
            self.session.query(AuthUser)
            .filter(AuthUser.tenant_id == tenant_id, AuthUser.username == username)
            .first()
        )
        if not user or not user.is_active:
            raise ValueError("Invalid credentials")

        cred = self.session.get(AuthCredential, user.id)
        if not cred or not verify_password(password, cred.password_hash):
            raise ValueError("Invalid credentials")

        return user

    def add_membership(
        self,
        *,
        tenant_id: str,
        org_id: str,
        user_id: int,
        roles: Optional[List[str]] = None,
    ) -> OrgMembership:
        membership = (
            self.session.query(OrgMembership)
            .filter(
                OrgMembership.tenant_id == tenant_id,
                OrgMembership.org_id == org_id,
                OrgMembership.user_id == user_id,
            )
            .first()
        )
        if membership:
            membership.roles = roles or []
            membership.is_active = True
            self.session.flush()
            return membership

        membership = OrgMembership(
            tenant_id=tenant_id,
            org_id=org_id,
            user_id=user_id,
            roles=roles or [],
            is_active=True,
        )
        self.session.add(membership)
        self.session.flush()
        return membership

    def list_orgs_for_user(self, *, tenant_id: str, user_id: int) -> List[Organization]:
        org_ids = [
            m.org_id
            for m in self.session.query(OrgMembership)
            .filter(
                OrgMembership.tenant_id == tenant_id,
                OrgMembership.user_id == user_id,
                OrgMembership.is_active.is_(True),
            )
            .all()
        ]
        if not org_ids:
            return []
        return (
            self.session.query(Organization)
            .filter(Organization.tenant_id == tenant_id, Organization.id.in_(org_ids))
            .all()
        )

    def get_roles_for_user_org(
        self, *, tenant_id: str, org_id: str, user_id: int
    ) -> List[str]:
        membership = (
            self.session.query(OrgMembership)
            .filter(
                OrgMembership.tenant_id == tenant_id,
                OrgMembership.org_id == org_id,
                OrgMembership.user_id == user_id,
                OrgMembership.is_active.is_(True),
            )
            .first()
        )
        if not membership:
            raise PermissionError("User is not a member of this organization")
        roles = membership.roles or []
        return [str(r) for r in roles]

