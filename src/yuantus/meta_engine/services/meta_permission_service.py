from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.meta_schema import ItemType
from ..permission.models import Access
from ..lifecycle.models import LifecycleState, StateIdentityPermission
from ..schemas.aml import AMLAction


class MetaPermissionService:
    """
    Service for handling unified permission checks (ACL + State-based + Dynamic).
    ADR-002 Implementation.
    """

    def __init__(self, session: Session):
        self.session = session

    def check_permission(
        self,
        item_type_id: Optional[str] = None,
        action: AMLAction = AMLAction.get,
        user_id: str = "guest",
        user_roles: List[str] = None,
        item_state: Optional[str] = None,
        item_owner_id: Optional[str] = None,
        permission_id: Optional[str] = None,
    ) -> bool:
        """
        Check if user has permission to perform action.

        Args:
            item_type_id: The ItemType ID (e.g. "Part"). Optional if permission_id provided.
            action: AMLAction.
            user_id: Current user's ID.
            user_roles: List of roles.
            item_state: Current logical state name.
            item_owner_id: ID of the user who owns the item.
            permission_id: Explicit permission set ID to check against (bypasses ItemType lookup).
        """

        # Expanded roles include user_id itself (for direct assignment) and "World"
        effective_roles = set(user_roles) if user_roles else set()
        effective_roles.add(user_id)
        effective_roles.add("world")
        # Admin and superuser roles bypass all permission checks
        if "admin" in effective_roles or "superuser" in effective_roles:
            return True

        base_permission_id = permission_id
        state_identity_perms = []

        # 1. Resolve Permissions Source (State vs ItemType) if not explicitly provided
        if not base_permission_id and item_type_id:
            item_type = (
                self.session.query(ItemType).filter(ItemType.id == item_type_id).first()
            )

            # If state context exists, check for state-specific permission overrides
            if item_state and item_type and item_type.lifecycle_map_id:
                lc_state = (
                    self.session.query(LifecycleState)
                    .filter(
                        LifecycleState.lifecycle_map_id == item_type.lifecycle_map_id
                    )
                    .filter(LifecycleState.name == item_state)
                    .first()
                )

                if lc_state:
                    if lc_state.permission_id:
                        base_permission_id = lc_state.permission_id
                    state_identity_perms = lc_state.identity_permissions

            # Fallback to ItemType default permission
            if not base_permission_id and item_type:
                base_permission_id = item_type.permission_id

        if not base_permission_id and not state_identity_perms:
            return False

        # 2. Check Base ACL (Permission Set + ACEs)
        if base_permission_id:
            if self._check_acl(
                base_permission_id, action, effective_roles, item_owner_id, user_id
            ):
                return True

        # 3. Check State-Identity specific overrides
        if state_identity_perms:
            if self._check_state_identity(
                state_identity_perms, action, effective_roles, item_owner_id, user_id
            ):
                return True

        return False

    def _check_acl(
        self,
        permission_id: str,
        action: AMLAction,
        effective_roles: set,
        item_owner_id: str,
        user_id: str,
    ) -> bool:
        """Check standard Access Control List"""
        aces = (
            self.session.query(Access)
            .filter(Access.permission_id == permission_id)
            .all()
        )
        for ace in aces:
            # Match Identity
            identity_match = False

            # Static Identity (Role/User)
            if ace.identity_id in effective_roles:
                identity_match = True

            # Dynamic Identity Check (e.g., if ace.identity_id is a placeholder for 'Creator')
            # NOTE: Access table usually stores specific IDs.
            # If we store "Creator" reserved word in Access.identity_id:
            if (
                ace.identity_id == "Creator"
                and item_owner_id
                and user_id == item_owner_id
            ):
                identity_match = True
            elif (
                ace.identity_id == "Owner"
                and item_owner_id
                and user_id == item_owner_id
            ):
                identity_match = True

            if identity_match:
                if self._action_allowed(ace, action):
                    return True
        return False

    def _check_state_identity(
        self,
        perms: List[StateIdentityPermission],
        action: AMLAction,
        effective_roles: set,
        item_owner_id: str,
        user_id: str,
    ) -> bool:
        """Check State-Identity Permission extensions"""
        for p in perms:
            identity_match = False

            if p.identity_type == "role":
                if p.identity_value in effective_roles:
                    identity_match = True
            elif p.identity_type == "dynamic":
                if (
                    p.identity_value in ["Creator", "Owner"]
                    and item_owner_id
                    and user_id == item_owner_id
                ):
                    identity_match = True

            if identity_match:
                # Check specific bits in StateIdentityPermission
                if action == AMLAction.get and p.can_read:
                    return True
                if action == AMLAction.update and p.can_update:
                    return True
                if action == AMLAction.delete and p.can_delete:
                    return True
                if action == AMLAction.promote and p.can_promote:
                    return True
                # logic for add? usually state permissions apply to existing items, so 'add' is moot here
                # unless it's the start state logic.

        return False

    def _action_allowed(self, ace: Access, action: AMLAction) -> bool:
        if action == AMLAction.get:
            return ace.can_get
        if action == AMLAction.add:
            return ace.can_create
        if action == AMLAction.update:
            return ace.can_update
        if action == AMLAction.delete:
            return ace.can_delete
        if action == AMLAction.promote:
            return ace.can_update  # Promote usually mapped to update or separate bit?
        return False
