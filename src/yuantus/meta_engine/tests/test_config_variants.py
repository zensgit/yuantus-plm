from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.configuration import (
    ConfigOption,
    ConfigOptionSet,
    OptionValueType,
    ProductConfiguration,
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


def test_compare_configurations_returns_selection_and_bom_diff():
    session = MagicMock(spec=Session)
    service = ConfigService(session)

    cfg_a = ProductConfiguration(
        id="cfg-a",
        product_item_id="PARENT",
        name="Config A",
        selections={"Color": "Red", "Voltage": 220},
        effective_bom_cache={"id": "PARENT", "children": []},
        state="draft",
        version=1,
    )
    cfg_b = ProductConfiguration(
        id="cfg-b",
        product_item_id="PARENT",
        name="Config B",
        selections={"Color": "Blue", "Voltage": 220},
        effective_bom_cache={"id": "PARENT", "children": []},
        state="draft",
        version=2,
    )

    def get_side_effect(model, pk):
        if pk == "cfg-a":
            return cfg_a
        if pk == "cfg-b":
            return cfg_b
        return None

    session.get.side_effect = get_side_effect
    service.bom_service.compare_bom_trees = MagicMock(return_value={"summary": {"changed": 1}})

    result = service.compare_configurations("cfg-a", "cfg-b")

    assert result["config_a"]["id"] == "cfg-a"
    assert result["config_b"]["id"] == "cfg-b"
    assert result["selection_differences"] == [
        {"option": "Color", "config_a": "Red", "config_b": "Blue"}
    ]
    assert result["bom_differences"]["summary"]["changed"] == 1
    service.bom_service.compare_bom_trees.assert_called_once_with(
        cfg_a.effective_bom_cache, cfg_b.effective_bom_cache
    )


def test_compare_configurations_raises_when_missing_config():
    session = MagicMock(spec=Session)
    service = ConfigService(session)
    session.get.return_value = None

    with pytest.raises(ValueError, match="Configuration not found"):
        service.compare_configurations("cfg-a", "cfg-b")
