from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    BigInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from yuantus.models.base import Base


class Tenant(Base):
    __tablename__ = "auth_tenants"

    id = Column(String(64), primary_key=True)
    name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Organization(Base):
    __tablename__ = "auth_organizations"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_tenant_org"),)

    id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), ForeignKey("auth_tenants.id"), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")


class AuthUser(Base):
    __tablename__ = "auth_users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_auth_user_tenant_username"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), ForeignKey("auth_tenants.id"), nullable=False, index=True)
    username = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")


class AuthCredential(Base):
    __tablename__ = "auth_credentials"

    user_id = Column(Integer, ForeignKey("auth_users.id", ondelete="CASCADE"), primary_key=True)
    password_hash = Column(String(500), nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship("AuthUser", backref="credential")


class OrgMembership(Base):
    __tablename__ = "auth_org_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "org_id", "user_id", name="uq_auth_membership"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), ForeignKey("auth_tenants.id"), nullable=False, index=True)
    org_id = Column(String(64), ForeignKey("auth_organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("auth_users.id"), nullable=False, index=True)

    roles = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
    org = relationship("Organization")
    user = relationship("AuthUser")


class TenantQuota(Base):
    __tablename__ = "auth_tenant_quotas"

    tenant_id = Column(
        String(64), ForeignKey("auth_tenants.id", ondelete="CASCADE"), primary_key=True
    )
    max_users = Column(Integer, nullable=True)
    max_orgs = Column(Integer, nullable=True)
    max_files = Column(Integer, nullable=True)
    max_storage_bytes = Column(BigInteger, nullable=True)
    max_active_jobs = Column(Integer, nullable=True)
    max_processing_jobs = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tenant = relationship("Tenant")
