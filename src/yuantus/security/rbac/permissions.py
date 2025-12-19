from __future__ import annotations

"""
RBAC Permission Manager (MVP)

This module exists to satisfy the migrated Meta Engine services (e.g. ECOService)
that expect a central permission manager.

For now (dev/MVP) we implement an "allow by default" policy so the functional
flows (ECO/Versioning) can be exercised before full auth/RBAC is wired in.
"""

from typing import Optional

from yuantus.exceptions.handlers import PermissionError


class PermissionManager:
    def __init__(self, *, enforce: bool = False) -> None:
        self.enforce = enforce

    def check_permission(
        self,
        user_id: int,
        action: str,
        resource: str,
        *,
        resource_id: Optional[str] = None,
        field: Optional[str] = None,
    ) -> bool:
        """
        MVP behavior:
        - enforce=False: always allow
        - enforce=True: deny everything unless user_id == 1
        """
        if not self.enforce:
            return True

        if user_id == 1:
            return True

        details = {"action": action, "resource": resource, "resource_id": resource_id}
        if field:
            details["field"] = field
        raise PermissionError(action=action, resource=resource, details=details)

