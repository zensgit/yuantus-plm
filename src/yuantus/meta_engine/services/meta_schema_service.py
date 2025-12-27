import hashlib
import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from ..models.meta_schema import ItemType
from yuantus.integrations.cad_connectors import resolve_cad_sync_key


class MetaSchemaService:
    """
    Service for managing ItemType schemas (Metadata True Source).
    ADR-001 Implementation.
    """

    def __init__(self, session: Session, redis_client=None):
        self.session = session
        self.redis_client = redis_client  # Optional: Future-proofing for external cache

    def get_json_schema(self, item_type_id: str) -> Dict[str, Any]:
        """
        Get the JSON schema for a given ItemType.
        Prioritizes the cached 'properties_schema' field.
        Falls back to generating it from the 'Property' table if empty.
        """
        item_type = (
            self.session.query(ItemType).filter(ItemType.id == item_type_id).first()
        )
        if not item_type:
            raise ValueError(f"ItemType '{item_type_id}' not found.")

        # Return cached schema if available
        if item_type.properties_schema:
            return item_type.properties_schema

        # Fallback: Generate from relational definition
        return self._generate_schema_from_properties(item_type)

    def get_schema_etag(self, item_type_id: str) -> str:
        """
        Compute ETag for the schema.
        Cheap way: Hash the JSON schema content.
        Optimization: Could hash updated_at timestamp if available on ItemType.
        """
        schema = self.get_json_schema(item_type_id)
        schema_str = json.dumps(schema, sort_keys=True)
        etag = hashlib.md5(schema_str.encode("utf-8")).hexdigest()

        if self.redis_client:
            try:
                self.redis_client.set(f"schema_etag:{item_type_id}", etag, ex=3600)
            except Exception:
                pass  # Ignore cache errors

        return etag

    def invalidate_cache(self, item_type_id: str):
        """
        Invalidate the DB-stored JSON schema cache.
        Should be called when Properties are modified.
        """
        item_type = (
            self.session.query(ItemType).filter(ItemType.id == item_type_id).first()
        )
        if item_type:
            item_type.properties_schema = None
            self.session.add(item_type)
            self.session.commit()

            if self.redis_client:
                self.redis_client.delete(f"schema_etag:{item_type_id}")

    def _generate_schema_from_properties(self, item_type: ItemType) -> Dict[str, Any]:
        """
        Generates a JSON Schema standard representation from relational properties.
        """
        schema = {
            "type": "object",
            "title": item_type.label or item_type.id,
            "description": item_type.description,
            "properties": {},
            "required": [],
        }

        # Need to fetch properties via relationship
        # Ensure properties are loaded
        for prop in item_type.properties:
            prop_def = {
                "type": self._map_data_type(prop.data_type),
                "title": prop.label,
                # JSON Schema built-in
                "maxLength": prop.length,
                "default": prop.default_value,
            }

            # Add new UI metadata fields
            prop_def["ui_type"] = prop.ui_type
            if prop.ui_options:
                prop_def["ui_options"] = prop.ui_options
            if prop.is_cad_synced:
                prop_def["x-cad-synced"] = True  # Use x- custom extension
                cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
                if cad_key and cad_key != prop.name:
                    prop_def["x-cad-key"] = cad_key
            if prop.default_value_expression:
                prop_def["x-default-value-expression"] = prop.default_value_expression

            # Helper for specific types
            if prop.data_type == "item" and prop.data_source_id:
                prop_def["x-item-type"] = prop.data_source_id

            schema["properties"][prop.name] = prop_def

            if prop.is_required:
                schema["required"].append(prop.name)

        return schema

    def _map_data_type(self, plm_type: str) -> str:
        """Map PLM types to JSON Schema types"""
        mapping = {
            "string": "string",
            "integer": "integer",
            "float": "number",
            "boolean": "boolean",
            "date": "string",  # format: date
            "item": "string",  # UUID
            "list": "array",
            "json": "object",
        }
        return mapping.get(plm_type, "string")

    def update_cached_schema(self, item_type_id: str) -> Dict[str, Any]:
        """
        Force updates the 'properties_schema' column based on current Property rows.
        Useful after altering properties via checking-out modification.
        """
        item_type = (
            self.session.query(ItemType).filter(ItemType.id == item_type_id).first()
        )
        if not item_type:
            raise ValueError(f"ItemType '{item_type_id}' not found.")

        schema = self._generate_schema_from_properties(item_type)
        item_type.properties_schema = schema
        self.session.add(item_type)
        self.session.commit()
        return schema

    def get_full_definition(self, item_type_id: str) -> Dict[str, Any]:
        """
        Aggregates Schema, Layout, and Metadata for Frontend consumption.
        """
        item_type = self.session.query(ItemType).get(item_type_id)
        if not item_type:
            raise ValueError(f"ItemType {item_type_id} not found")

        # Get JSON Schema (Data validation)
        json_schema = self.get_json_schema(item_type_id)

        # Get UI Layout
        ui_layout_raw = item_type.ui_layout
        if ui_layout_raw:
            if isinstance(ui_layout_raw, str):
                ui_layout = json.loads(ui_layout_raw)
            else:  # Already a dict from some SQLAlchemy JSON processing
                ui_layout = ui_layout_raw
        else:
            ui_layout = self._generate_default_layout(item_type)

        return {
            "id": item_type.id,
            "label": item_type.label,
            "description": item_type.description,
            "schema": json_schema,
            "layout": ui_layout,
            "lifecycle_id": item_type.lifecycle_map_id,
        }

    def _generate_default_layout(self, item_type: ItemType) -> Dict[str, Any]:
        """
        Auto-generates a default Form and List layout based on properties.
        """
        fields = [p.name for p in item_type.properties]

        # Simple default list: first 5 fields
        list_cols = [{"name": f} for f in fields[:5]]

        # Simple default form: all fields in a single group
        form_children = [{"type": "field", "name": f} for f in fields]

        return {
            "list": {"columns": list_cols},
            "form": {
                "type": "form",
                "layout": {"type": "group", "children": form_children},
            },
        }
