from typing import Dict, Any
from sqlalchemy import select
from .base import BaseOperation
from ..models.item import Item
from ..models.meta_schema import ItemType
from yuantus.meta_engine.schemas.aml import AMLAction, GenericItem
from yuantus.exceptions.handlers import PermissionError

class GetOperation(BaseOperation):
    """
    Handles AML 'get' action.
    """
    def execute(self, item_type: ItemType, aml: GenericItem) -> Dict[str, Any]:
        stmt = select(Item).where(Item.item_type_id == item_type.id, Item.is_current)

        if aml.id:
            stmt = stmt.where(Item.id == aml.id)

        # JSONB Query Construction
        post_filters: Dict[str, Any] = {}
        if aml.properties:
            for key, value in aml.properties.items():
                json_field = Item.properties[key]
                if hasattr(json_field, "as_string"):
                    stmt = stmt.where(json_field.as_string() == str(value))
                elif hasattr(json_field, "astext"):
                    stmt = stmt.where(json_field.astext == str(value))
                else:
                    post_filters[key] = value

        result = self.session.execute(stmt).scalars().all()
        
        # Post-process filters (for complex logic not handled by SQL)
        if post_filters:
            result = [
                item
                for item in result
                if all(
                    str(item.properties.get(k)) == str(v)
                    for k, v in post_filters.items()
                )
            ]

        # Field Selection
        requested_fields = getattr(aml, "_fields", None)

        # Permission Filtering
        visible = [
            item
            for item in result
            if self.permission_service.check_permission(
                item.item_type_id,
                AMLAction.get,
                self.user_id,
                self.roles,
                item_state=item.state,
                item_owner_id=str(item.created_by_id) if item.created_by_id else None,
            )
        ]

        if result and not visible:
            raise PermissionError(action=AMLAction.get.value, resource=item_type.id)

        return {
            "count": len(visible),
            "items": [self._dump_item(item, requested_fields) for item in visible],
        }

    def _dump_item(self, item, requested_fields):
        d = {
            "id": item.id,
            "type": item.item_type_id,
            "state": item.state,
            "properties": item.properties,
        }

        if requested_fields:
            out = {}
            for f in requested_fields:
                if f in ["id", "type", "state", "config_id", "generation"]:
                    out[f] = getattr(item, f)
                elif f in item.properties:
                    out[f] = item.properties[f]
                elif f == "properties":
                    out["properties"] = item.properties
            
            # Maintain properties structure for frontend compatibility
            filtered_props = {}
            for k, v in item.properties.items():
                if k in requested_fields:
                    filtered_props[k] = v
            d["properties"] = filtered_props
            
        return d
