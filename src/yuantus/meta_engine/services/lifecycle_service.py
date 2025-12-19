"""
Lifecycle Service
Manages Workflow Definitions and Transitions for Meta Engine Items.
Phase 3: Workflow Engine
"""

import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from yuantus.meta_engine.lifecycle.models import (
    LifecycleMap,
    LifecycleState,
    LifecycleTransition,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.security.rbac.models import RBACRole, RBACUser


class LifecycleService:
    def __init__(self, session: Session):
        self.session = session

    # --- Definition API ---
    def create_lifecycle(self, name: str, description: str = None) -> LifecycleMap:
        """Create a new Lifecycle Map (Workflow Definition)."""
        lc = LifecycleMap(id=str(uuid.uuid4()), name=name, description=description)
        self.session.add(lc)
        self.session.flush()
        return lc

    def add_state(
        self,
        lifecycle_id: str,
        name: str,
        label: str = None,
        is_start: bool = False,
        is_end: bool = False,
        sequence: int = 0,
    ) -> LifecycleState:
        """Add a state to a lifecycle."""
        # If is_start, unset other start states for this lifecycle
        if is_start:
            self.session.query(LifecycleState).filter_by(
                lifecycle_map_id=lifecycle_id, is_start_state=True
            ).update({"is_start_state": False})

        state = LifecycleState(
            id=str(uuid.uuid4()),
            lifecycle_map_id=lifecycle_id,
            name=name,
            label=label or name,
            is_start_state=is_start,
            # is_end_state=is_end,
            sequence=sequence,
        )
        self.session.add(state)
        self.session.flush()
        return state

    def add_transition(
        self,
        lifecycle_id: str,
        from_state_name: str,
        to_state_name: str,
        action_name: str,
        roles: List[str] = None,
    ) -> LifecycleTransition:
        """Add a transition between two states."""
        # Resolve state IDs by name within this lifecycle
        from_state = (
            self.session.query(LifecycleState)
            .filter_by(lifecycle_map_id=lifecycle_id, name=from_state_name)
            .first()
        )
        to_state = (
            self.session.query(LifecycleState)
            .filter_by(lifecycle_map_id=lifecycle_id, name=to_state_name)
            .first()
        )

        if not from_state or not to_state:
            raise ValueError(
                f"State not found: '{from_state_name}' or '{to_state_name}' in lifecycle {lifecycle_id}"
            )

        # Map roles list to role_allowed_id (use first role if provided)
        role_allowed_id = None
        if roles and len(roles) > 0:
            role = self.session.query(RBACRole).filter_by(name=roles[0]).first()
            if role:
                role_allowed_id = role.id

        transition = LifecycleTransition(
            id=str(uuid.uuid4()),
            lifecycle_map_id=lifecycle_id,
            from_state_id=from_state.id,
            to_state_id=to_state.id,
            action_name=action_name,
            role_allowed_id=role_allowed_id,
        )
        self.session.add(transition)
        self.session.flush()
        return transition

    # --- Configuration API ---
    def assign_lifecycle_to_type(self, item_type_id: str, lifecycle_id: str):
        """Bind a lifecycle to an ItemType."""
        itype = self.session.query(ItemType).get(item_type_id)
        if not itype:
            raise ValueError(f"ItemType {item_type_id} not found")
        itype.lifecycle_map_id = lifecycle_id
        self.session.add(itype)
        self.session.flush()

    # --- Runtime API ---
    def init_item_lifecycle(self, item: Item):
        """
        Set item to the start state of its configured lifecycle.
        Should be called on Item creation.
        """
        # Get ItemType
        itype = self.session.query(ItemType).get(item.item_type_id)
        if not itype or not itype.lifecycle_map_id:
            return  # No lifecycle configured

        start_state = (
            self.session.query(LifecycleState)
            .filter_by(lifecycle_map_id=itype.lifecycle_map_id, is_start_state=True)
            .first()
        )

        if start_state:
            item.current_state = start_state.id
            item.state = start_state.label or start_state.name
            self.session.add(item)
            self.session.flush()

    def get_available_transitions(
        self, item_id: str, user_id: int
    ) -> List[Dict[str, Any]]:
        """Get list of possible transitions for an item based on its current state and user permissions."""
        item = self.session.query(Item).get(item_id)
        if not item or not item.current_state:
            return []

        # Get current state record to find lifecycle_id
        current_state_rec = self.session.query(LifecycleState).get(item.current_state)
        if not current_state_rec:
            return []

        transitions = (
            self.session.query(LifecycleTransition)
            .filter_by(
                lifecycle_map_id=current_state_rec.lifecycle_map_id,
                from_state_id=item.current_state,
            )
            .all()
        )

        # Get user's role IDs for permission filtering
        user = self.session.query(RBACUser).filter_by(id=user_id).first()
        user_role_ids = set()
        if user:
            user_role_ids = {r.id for r in user.roles}
            # Superuser can access all transitions
            if user.is_superuser:
                user_role_ids = None  # None means no filtering

        result = []
        for t in transitions:
            # Filter by role permission
            if user_role_ids is not None and t.role_allowed_id:
                if t.role_allowed_id not in user_role_ids:
                    continue  # User doesn't have required role

            to_state = self.session.query(LifecycleState).get(t.to_state_id)
            result.append(
                {
                    "action": t.action_name,
                    "to_state": to_state.name,
                    "to_state_label": to_state.label,
                    "role_required": t.role_allowed.name if t.role_allowed else None,
                }
            )
        return result

    def promote_item(
        self, item_id: str, action_name: str, user_id: int, model_cls=Item
    ) -> Any:
        """
        Execute a lifecycle transition with permission check.
        """
        item = self.session.query(model_cls).get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        if not item.current_state:
            raise ValueError("Item has no lifecycle state assigned")

        # Get current state record
        current_state_rec = self.session.query(LifecycleState).get(item.current_state)
        if not current_state_rec:
            raise ValueError("Invalid current state ID on item")

        # Find transition
        transition = (
            self.session.query(LifecycleTransition)
            .filter_by(
                lifecycle_map_id=current_state_rec.lifecycle_map_id,
                from_state_id=item.current_state,
                action_name=action_name,
            )
            .first()
        )

        if not transition:
            raise ValueError(
                f"No transition found for action '{action_name}' from state '{current_state_rec.name}'"
            )

        # Check permissions
        if transition.role_allowed_id:
            user = self.session.query(RBACUser).filter_by(id=user_id).first()
            if not user:
                raise PermissionError(f"User {user_id} not found")

            # Superuser bypass
            if not user.is_superuser:
                user_role_ids = {r.id for r in user.roles}
                if transition.role_allowed_id not in user_role_ids:
                    role_name = (
                        transition.role_allowed.name
                        if transition.role_allowed
                        else "unknown"
                    )
                    raise PermissionError(
                        f"User does not have required role '{role_name}' for action '{action_name}'"
                    )

        # Execute Transition
        target_state = self.session.query(LifecycleState).get(transition.to_state_id)

        # Update Item
        item.current_state = target_state.id
        item.state = target_state.label or target_state.name

        self.session.add(item)
        self.session.commit()
        return item


class PermissionError(Exception):
    """Raised when user lacks permission for an operation."""

    pass
