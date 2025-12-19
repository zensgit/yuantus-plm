from typing import Dict, Any, TYPE_CHECKING
from .base import BaseOperation
from ..models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem
from yuantus.exceptions.handlers import PermissionError, ValidationError
from yuantus.meta_engine.events.domain_events import ItemStateChangedEvent
from yuantus.meta_engine.events.transactional import enqueue_event

if TYPE_CHECKING:
    from ..models.meta_schema import ItemType

class PromoteOperation(BaseOperation):
    """
    Handles AML 'promote' action (Lifecycle transition).
    """
    def execute(self, item_type: 'ItemType', aml: GenericItem) -> Dict[str, Any]:
        if not aml.id:
            raise ValidationError("Promote requires an item id", field="id")
            
        item = self.session.get(Item, aml.id)
        if not item or item.item_type_id != item_type.id:
            raise ValidationError("Item not found for promotion", field="id")

        if not self.permission_service.check_permission(
            item_type.id,
            AMLAction.promote,
            self.user_id,
            self.roles,
            item_state=item.state,
            item_owner_id=str(item.created_by_id) if item.created_by_id else None,
        ):
            raise PermissionError(action=AMLAction.promote.value, resource=item_type.id)
            
        target_state = aml.properties.get("target_state")
        if not target_state:
            raise ValidationError(
                "target_state is required for promote", field="target_state"
            )

        try:
            user_id_int = (
                int(self.user_id) if self.user_id and str(self.user_id).isdigit() else 0
            )
        except Exception:
            user_id_int = 0

        old_state_name = item.state or ""

        # Access lifecycle service via engine
        result = self.engine.lifecycle.promote(
            item,
            target_state_name=str(target_state),
            user_id=user_id_int,
        )

        if not result.success:
            raise ValidationError(f"Promote failed: {result.error}", field="state")

        self.session.flush()
        
        enqueue_event(
            self.session,
            ItemStateChangedEvent(
                item_id=item.id,
                item_type_id=item_type.id,
                old_state=old_state_name,
                new_state=item.state,
                transition_name=str(target_state),
                actor_id=int(self.user_id) if self.user_id.isdigit() else None,
            )
        )
        return {
            "id": item.id,
            "type": item.item_type_id,
            "state": item.state,
            "current_state": item.current_state,
        }
