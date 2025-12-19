"""
RBAC Models - minimal baseline for Meta Engine references.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from yuantus.models.base import Base

logger = logging.getLogger(__name__)

rbac_metadata = Base.metadata
RBACBase = Base

rbac_user_roles = Table(
    "rbac_user_roles",
    rbac_metadata,
    Column("user_id", Integer, ForeignKey("rbac_users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("rbac_roles.id"), primary_key=True),
    Column("assigned_at", DateTime, default=datetime.now),
    extend_existing=True,
)

role_permissions = Table(
    "rbac_role_permissions",
    rbac_metadata,
    Column("role_id", Integer, ForeignKey("rbac_roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("rbac_permissions.id"), primary_key=True),
    Column("granted_at", DateTime, default=datetime.now),
    Column("granted_by", Integer, ForeignKey("rbac_users.id")),
    extend_existing=True,
)

rbac_user_permissions = Table(
    "rbac_user_permissions",
    rbac_metadata,
    Column("user_id", Integer, ForeignKey("rbac_users.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("rbac_permissions.id"), primary_key=True),
    Column("granted_at", DateTime, default=datetime.now),
    Column("is_denied", Boolean, default=False),
    extend_existing=True,
)


class RBACResource(RBACBase):
    __tablename__ = "rbac_resources"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    resource_type = Column(String(50), nullable=False)
    description = Column(Text)

    parent_id = Column(Integer, ForeignKey("rbac_resources.id"))
    parent = relationship("RBACResource", remote_side=[id], backref="children")

    resource_metadata = Column(Text)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RBACPermission(RBACBase):
    __tablename__ = "rbac_permissions"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    action = Column(String(50), nullable=False)
    resource_id = Column(Integer, ForeignKey("rbac_resources.id"), nullable=False)

    resource = relationship("RBACResource", backref="permissions")

    description = Column(Text)
    conditions = Column(Text)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class RBACRole(RBACBase):
    __tablename__ = "rbac_roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200))
    description = Column(Text)

    parent_id = Column(Integer, ForeignKey("rbac_roles.id"))
    parent = relationship("RBACRole", remote_side=[id], backref="children")

    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)

    permissions = relationship("RBACPermission", secondary=role_permissions, backref="roles")

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def has_permission(self, permission_name: str) -> bool:
        for permission in self.permissions:
            if permission.name == permission_name and permission.is_active:
                return True
        if self.parent:
            return self.parent.has_permission(permission_name)
        return False

    def get_all_permissions(self) -> List["RBACPermission"]:
        permissions = list(self.permissions)
        if self.parent:
            permissions.extend(self.parent.get_all_permissions())

        seen = set()
        unique: List["RBACPermission"] = []
        for perm in permissions:
            if perm.id not in seen:
                seen.add(perm.id)
                unique.append(perm)
        return unique


class RBACUser(RBACBase):
    __tablename__ = "rbac_users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200))

    roles = relationship("RBACRole", secondary=rbac_user_roles, backref="users")
    direct_permissions = relationship(
        "RBACPermission",
        secondary=rbac_user_permissions,
        backref="direct_users",
    )

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    last_login = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def has_permission(self, permission_name: str) -> bool:
        if self.is_superuser:
            return True

        for permission in self.direct_permissions:
            if permission.name == permission_name and permission.is_active:
                return True

        for role in self.roles:
            if role.is_active and role.has_permission(permission_name):
                return True

        return False

