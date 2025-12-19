import json
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError as JSONSchemaValidationError

from yuantus.exceptions.handlers import ValidationError
from ..models.meta_schema import ItemType, Property

class MetaValidator:
    """
    Handles validation and normalization of Item properties against ItemType definition.
    """
    
    def validate_and_normalize(
        self, item_type: ItemType, properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and normalize item properties against ItemType's properties_schema.
        """
        normalized = dict(properties or {})

        # 1. Perform JSON Schema validation if schema is defined
        if item_type.properties_schema:
            try:
                schema_raw = item_type.properties_schema
                if isinstance(schema_raw, str):
                    schema = json.loads(schema_raw)
                elif isinstance(schema_raw, dict):
                    schema = schema_raw
                else:
                    raise ValidationError(
                        f"Invalid properties_schema for ItemType {item_type.id}",
                        field="properties_schema",
                    )
                validate(instance=normalized, schema=schema)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    f"Invalid JSON Schema for ItemType {item_type.id}: {exc}"
                ) from exc
            except JSONSchemaValidationError as exc:
                field_name = exc.path[0] if exc.path else None
                raise ValidationError(
                    f"Properties do not conform to schema for ItemType {item_type.id}: {exc.message}",
                    field=field_name,  # Pass field name here
                ) from exc

        # 2. Perform basic type casting and required checks
        definitions = {p.name: p for p in (item_type.properties or [])}

        for name, prop in definitions.items():
            has_value = name in normalized and normalized[name] is not None
            if not has_value:
                if prop.is_required and (
                    not item_type.properties_schema
                ):  # Only if not already validated by JSON Schema
                    raise ValidationError(f"Property '{name}' is required", field=name)
                elif prop.default_value is not None:
                    normalized[name] = self._cast_value(prop, prop.default_value)
                else:
                    continue
            else:
                normalized[name] = self._cast_value(prop, normalized[name])

            # Length check only after casting
            if prop.length and isinstance(normalized[name], str):
                if len(normalized[name]) > prop.length:
                    raise ValidationError(
                        f"Property '{name}' exceeds max length {prop.length}",
                        field=name,
                    )
        return normalized

    def _cast_value(self, prop: Property, value: Any) -> Any:
        """Cast value according to meta property definition."""
        data_type = (prop.data_type or "").lower()

        if value is None:
            return None

        try:
            if data_type == "string":
                return str(value)
            if data_type == "integer":
                return int(value)
            if data_type == "float":
                return float(value)
            if data_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    lowered = value.lower()
                    if lowered in {"true", "1", "yes", "y"}:
                        return True
                    if lowered in {"false", "0", "no", "n"}:
                        return False
                return bool(value)
            if data_type == "json":
                if isinstance(value, (dict, list)):
                    return value
                if isinstance(value, str):
                    return json.loads(value)
            if data_type == "list":
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    candidate = json.loads(value)
                    if not isinstance(candidate, list):
                        raise ValidationError(
                            f"Property '{prop.name}' expects a list", field=prop.name
                        )
                    return candidate
                raise ValidationError(
                    f"Property '{prop.name}' expects a list", field=prop.name
                )
            if data_type == "item":
                # For now, only enforce ID shape; referential checks can be added later
                return str(value)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValidationError(
                f"Property '{prop.name}' expects {data_type}", field=prop.name
            ) from exc

        # Default passthrough
        return value
