from typing import Dict, Any, TYPE_CHECKING
from .base import BaseOperation
from ..models.item import Item
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem
from yuantus.exceptions.handlers import PermissionError, ValidationError
from yuantus.meta_engine.events.domain_events import ItemDeletedEvent
from yuantus.meta_engine.events.transactional import enqueue_event

if TYPE_CHECKING:
    from ..models.meta_schema import ItemType

class DeleteOperation(BaseOperation):
    """
    Handles AML 'delete' action.
    """
    def execute(self, item_type: 'ItemType', aml: GenericItem) -> Dict[str, Any]:
        if not aml.id:
            raise ValidationError("Delete requires an item id", field="id")
        
        item = self.session.get(Item, aml.id)
        if not item or item.item_type_id != item_type.id:
            raise ValidationError("Item not found for delete", field="id")

        if not self.permission_service.check_permission(
            item_type.id,
            AMLAction.delete,
            self.user_id,
            self.roles,
            item_state=item.state,
            item_owner_id=str(item.created_by_id) if item.created_by_id else None,
        ):
            raise PermissionError(action=AMLAction.delete.value, resource=item_type.id)

        self.session.delete(item)
        self.session.flush()
        
        enqueue_event(
            self.session,
            ItemDeletedEvent(
                item_id=aml.id,
                item_type_id=item_type.id,
                actor_id=int(self.user_id) if self.user_id.isdigit() else None,
            )
        )
        return {"id": aml.id, "type": item_type.id, "status": "deleted"}
