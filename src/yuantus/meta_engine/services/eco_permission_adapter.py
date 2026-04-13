"""
EcoPermissionAdapter -- bridges ECO actions to the unified MetaPermissionService.

Maintains the same ``check_permission(user_id, action, resource, *, resource_id, field)``
signature used by the legacy PermissionManager so that ECOService call-sites
remain unchanged.

Graceful degradation: when MetaPermissionService has **no** rules configured for
the ECO ItemType (no ItemType row, no Permission set), the adapter falls back to
"allow by default" so the system keeps working during migration.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.models.eco import ECO
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.schemas.aml import AMLAction
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService

logger = logging.getLogger(__name__)

# Mapping from legacy action strings to AMLAction values.
_ACTION_MAP = {
    "create": AMLAction.add,
    "update": AMLAction.update,
    "execute": AMLAction.update,   # execute is a specialised update
    "delete": AMLAction.delete,
}

ECO_ITEM_TYPE = "ECO"


class EcoPermissionAdapter:
    """Drop-in replacement for ``PermissionManager`` inside ``ECOService``.

    Delegates to ``MetaPermissionService`` when ECO permission rules exist;
    falls back to allow-by-default otherwise (migration safety net).
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self._meta_service = MetaPermissionService(session)

    # ------------------------------------------------------------------
    # Public API -- same signature as PermissionManager.check_permission
    # ------------------------------------------------------------------
    def check_permission(
        self,
        user_id: int,
        action: str,
        resource: str,
        *,
        resource_id: Optional[str] = None,
        field: Optional[str] = None,
    ) -> bool:
        """Check permission, delegating to MetaPermissionService when possible."""

        # Only intercept ECO-related resources; pass-through others with allow.
        if resource != ECO_ITEM_TYPE:
            return True

        aml_action = _ACTION_MAP.get(action, AMLAction.update)

        # Resolve ECO state for state-based checks
        item_state: Optional[str] = None
        item_owner_id: Optional[str] = None
        if resource_id:
            eco = self.session.get(ECO, resource_id)
            if eco:
                item_state = eco.state
                item_owner_id = (
                    str(eco.created_by_id) if eco.created_by_id is not None else None
                )

        # Graceful degradation: if no rules are configured for ECO, allow.
        if not self._has_eco_rules():
            logger.debug(
                "No ECO permission rules configured -- falling back to allow "
                "(user=%s action=%s field=%s)",
                user_id,
                action,
                field,
            )
            return True

        user_roles = self._resolve_user_roles(user_id)

        return self._meta_service.check_permission(
            item_type_id=ECO_ITEM_TYPE,
            action=aml_action,
            user_id=str(user_id),
            user_roles=user_roles,
            item_state=item_state,
            item_owner_id=item_owner_id,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _has_eco_rules(self) -> bool:
        """Return True when the DB contains an ItemType row for ECO with a
        permission_id set (i.e. the admin has configured ACL rules)."""
        item_type = (
            self.session.query(ItemType)
            .filter(ItemType.id == ECO_ITEM_TYPE)
            .first()
        )
        if item_type and item_type.permission_id:
            return True
        return False

    def _resolve_user_roles(self, user_id: int) -> List[str]:
        """Thin wrapper reusing the same RBAC lookup pattern as ECOService."""
        from yuantus.security.rbac.models import RBACUser

        try:
            user = self.session.get(RBACUser, int(user_id))
        except Exception:
            return []
        if not user:
            return []
        roles: List[str] = []
        for role in getattr(user, "roles", []) or []:
            name = str(getattr(role, "name", "") or "").strip().lower()
            if name and name not in roles:
                roles.append(name)
        return roles
