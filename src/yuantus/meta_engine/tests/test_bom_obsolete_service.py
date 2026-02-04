from unittest.mock import MagicMock

import pytest

from yuantus.meta_engine.services.bom_obsolete_service import BOMObsoleteService


def _make_item(props=None, state=None, current_state=None, item_type_id="Part"):
    item = MagicMock()
    item.properties = props or {}
    item.state = state
    item.current_state = current_state
    item.item_type_id = item_type_id
    return item


def test_is_obsolete_state_flags_true():
    service = BOMObsoleteService(MagicMock())
    item = _make_item({"obsolete": True})
    assert service._is_obsolete_state(item) is True


def test_resolve_invalid_mode_raises():
    service = BOMObsoleteService(MagicMock())
    with pytest.raises(ValueError):
        service.resolve("root-item", mode="invalid")
