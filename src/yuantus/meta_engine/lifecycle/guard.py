from typing import Optional, Tuple

from sqlalchemy.orm import Session

from yuantus.meta_engine.lifecycle.models import LifecycleState
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType


def get_lifecycle_state(
    session: Session, item: Item, item_type: Optional[ItemType] = None
) -> Optional[LifecycleState]:
    if item.current_state:
        state = session.get(LifecycleState, item.current_state)
        if state:
            return state

    if item_type and item_type.lifecycle_map_id and item.state:
        return (
            session.query(LifecycleState)
            .filter(
                LifecycleState.lifecycle_map_id == item_type.lifecycle_map_id,
                LifecycleState.name == item.state,
            )
            .first()
        )

    return None


def is_item_locked(
    session: Session, item: Item, item_type: Optional[ItemType] = None
) -> Tuple[bool, Optional[str]]:
    state = get_lifecycle_state(session, item, item_type)
    if state and state.version_lock:
        return True, state.name
    return False, state.name if state else None
