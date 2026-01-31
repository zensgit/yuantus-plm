from __future__ import annotations

from typing import Any, Dict, List

from yuantus.meta_engine.models.configuration import ConfigOptionSet, OptionValueType


class ConfigSelectionValidator:
    def __init__(self, option_sets: List[ConfigOptionSet]):
        self.option_sets = option_sets

    def validate(self, selections: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for option_set in self.option_sets:
            key = option_set.name
            value = selections.get(key)

            if value is None:
                if option_set.is_required:
                    errors.append(f"Option '{key}' is required")
                continue

            values = value if isinstance(value, list) else [value]
            if not option_set.allow_multiple and len(values) > 1:
                errors.append(f"Option '{key}' does not allow multiple selections")

            active_options = [opt for opt in option_set.options if opt.is_active]
            if active_options:
                valid_values = {opt.value if opt.value is not None else opt.key for opt in active_options}
                valid_refs = {opt.ref_item_id for opt in active_options if opt.ref_item_id}
                for v in values:
                    if v in valid_values or v in valid_refs:
                        continue
                    errors.append(f"Invalid value '{v}' for option '{key}'")

            value_type = (option_set.value_type or OptionValueType.STRING.value).lower()
            if value_type == OptionValueType.NUMBER.value:
                for v in values:
                    if not _is_number(v):
                        errors.append(f"Option '{key}' expects number, got '{v}'")
            elif value_type == OptionValueType.BOOLEAN.value:
                for v in values:
                    if not _is_bool(v):
                        errors.append(f"Option '{key}' expects boolean, got '{v}'")
            elif value_type == OptionValueType.ITEM_REF.value:
                # When option items define ref_item_id, the valid_refs check above applies.
                # Otherwise, accept any string-like value.
                pass

        return errors


def _is_number(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)) and value in (0, 1):
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "false", "0", "1", "yes", "no"}
    return False
