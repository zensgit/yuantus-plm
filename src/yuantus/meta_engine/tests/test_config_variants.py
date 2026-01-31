from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from yuantus.meta_engine.models.configuration import (
    ConfigOption,
    ConfigOptionSet,
    OptionValueType,
    VariantRule,
)
from yuantus.meta_engine.services.config_service import ConfigService
from yuantus.meta_engine.services.config_validator import ConfigSelectionValidator


def test_config_selection_validator_errors():
    voltage = ConfigOptionSet(
        id="os-voltage",
        name="Voltage",
        value_type=OptionValueType.NUMBER.value,
        is_required=True,
        allow_multiple=False,
        is_active=True,
    )
    voltage.options = []

    enabled = ConfigOptionSet(
        id="os-enabled",
        name="Enabled",
        value_type=OptionValueType.BOOLEAN.value,
        is_required=False,
        allow_multiple=False,
        is_active=True,
    )
    enabled.options = []

    features = ConfigOptionSet(
        id="os-features",
        name="Features",
        value_type=OptionValueType.STRING.value,
        is_required=False,
        allow_multiple=False,
        is_active=True,
    )
    features.options = [
        ConfigOption(
            id="opt-a",
            option_set_id="os-features",
            key="A",
            value="A",
            is_active=True,
        ),
        ConfigOption(
            id="opt-b",
            option_set_id="os-features",
            key="B",
            value="B",
            is_active=True,
        ),
    ]

    validator = ConfigSelectionValidator([voltage, enabled, features])

    errors = validator.validate(
        {
            "Voltage": "abc",
            "Enabled": "maybe",
            "Features": ["A", "B"],
        }
    )

    assert "Option 'Voltage' expects number, got 'abc'" in errors
    assert "Option 'Enabled' expects boolean, got 'maybe'" in errors
    assert "Option 'Features' does not allow multiple selections" in errors

    missing_errors = validator.validate({})
    assert "Option 'Voltage' is required" in missing_errors


def test_variant_rule_excludes_child_when_condition_matches():
    session = MagicMock(spec=Session)
    service = ConfigService(session)

    bom = {
        "id": "PARENT",
        "children": [
            {
                "relationship": {
                    "id": "REL-1",
                    "properties": {},
                },
                "child": {"id": "CHILD-1", "children": []},
            }
        ],
    }

    rule = VariantRule(
        id="rule-1",
        name="Exclude Standard",
        condition={"option": "Mode", "value": "Standard"},
        action_type="exclude",
        target_item_id="CHILD-1",
        priority=100,
        is_active=True,
    )

    result_standard = service._apply_variant_rules(bom, [rule], {"Mode": "Standard"})
    assert len(result_standard.get("children") or []) == 0

    result_premium = service._apply_variant_rules(bom, [rule], {"Mode": "Premium"})
    assert len(result_premium.get("children") or []) == 1
