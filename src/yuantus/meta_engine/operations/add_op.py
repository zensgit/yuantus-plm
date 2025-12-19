from typing import Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session
from .base import BaseOperation
from ..models.item import Item
from ..models.meta_schema import ItemType
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem
from yuantus.exceptions.handlers import PermissionError, ValidationError
from yuantus.meta_engine.events.domain_events import ItemCreatedEvent
from yuantus.meta_engine.events.transactional import enqueue_event

class AddOperation(BaseOperation):
    """
    Handles AML 'add' action.
    """
    def execute(self, item_type: ItemType, aml: GenericItem, parent_item: Optional[Item] = None) -> Dict[str, Any]:
        # 0. Permission Check
        if not self.permission_service.check_permission(
            item_type.id, AMLAction.add, self.user_id, self.roles
        ):
            raise PermissionError(action=AMLAction.add.value, resource=item_type.id)

        # 1. Prepare properties
        raw_properties = dict(aml.properties or {})

        # 2. Relationship requires source
        if item_type.is_relationship and not parent_item:
            raise ValidationError("Relationship creation requires a source item")

        # 3. Create physical row
        new_item = Item(
            id=str(uuid.uuid4()),
            item_type_id=item_type.id,
            config_id=str(uuid.uuid4()),
            generation=1,
            properties=raw_properties,
            state="New",
            permission_id=item_type.permission_id,
            created_by_id=(
                int(self.user_id) if self.user_id and self.user_id.isdigit() else None
            ),
        )

        # 4. Handle Relationship Linkage
        if item_type.is_relationship and parent_item:
            new_item.source_id = parent_item.id
            if aml.properties.get("related_id"):
                new_item.related_id = aml.properties.get("related_id")

        # 5. Method Hook (onBeforeAdd)
        if item_type.on_before_add_method_id:
            new_item = self.engine.method_executor.execute_method(
                item_type.on_before_add_method_id, new_item, aml
            )

        # 6. Validate & Normalize
        # We access the engine's validator
        validated_props = self.engine.validator.validate_and_normalize(
            item_type, dict(new_item.properties or {})
        )
        new_item.properties = validated_props

        self.session.add(new_item)

        # 7. Attach Lifecycle
        self.engine.lifecycle.attach_lifecycle(item_type, new_item)

        # 8. Recursive Relationships (Deep Insert)
        if aml.relationships:
            for rel_aml in aml.relationships:
                self.engine.apply_relationship(rel_aml, source_item=new_item)

        self.session.flush()
        
        # 9. Publish Event
        enqueue_event(
            self.session,
            ItemCreatedEvent(
                item_id=new_item.id,
                item_type_id=item_type.id,
                properties=new_item.properties,
                actor_id=int(self.user_id) if self.user_id.isdigit() else None,
            )
        )
        return {"id": new_item.id, "type": item_type.id, "status": "created"}
