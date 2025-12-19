from typing import List, Optional
from sqlalchemy.orm import Session
from ..schemas.aml import AMLAction
from yuantus.exceptions.handlers import PermissionError
from .meta_permission_service import MetaPermissionService


class SecurityService:
    """
    Legacy Security Service wrapper.
    Delegates to MetaPermissionService.
    DEPRECATED: Use MetaPermissionService directly.
    """

    def __init__(self, session: Session, identity_id: Optional[str], roles: List[str]):
        self.session = session
        self.identity_id = identity_id or "guest"
        self.roles = roles or ["guest"]
        self.permission_service = MetaPermissionService(session)

    def can_access(self, permission_id: str, action: AMLAction) -> bool:
        """
        Check if current user has 'action' rights.
        Note: This legacy method cannot fully support state-based or owner-based
        dynamic permissions because it lacks context. It assumes 'Draft' or no state,
        and no ownership match.
        """
        return self.permission_service.check_permission(
            item_type_id=None,  # Cannot resolve item type from permission ID purely here
            permission_id=permission_id,  # Explicitly pass the ID we were asked about
            action=action,
            user_id=self.identity_id,
            user_roles=self.roles,
            item_state=None,
            item_owner_id=None,
        )

    def require_action(self, permission_id: str, action: AMLAction, resource: str):
        if not self.can_access(permission_id, action):
            raise PermissionError(action=action.value, resource=resource)
