from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from yuantus.meta_engine.lifecycle.models import LifecycleState
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.suspended_guard import (
    SuspendedGuardService,
    SuspendedStateError,
)
from yuantus.meta_engine.version.models import ItemVersion


class _Query:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


def _session_for(
    *,
    items: dict[str, Item] | None = None,
    item_types: dict[str, ItemType] | None = None,
    states: dict[str, LifecycleState] | None = None,
    versions: dict[str, ItemVersion] | None = None,
    query_result=None,
):
    session = MagicMock()
    items = items or {}
    item_types = item_types or {}
    states = states or {}
    versions = versions or {}

    def _get(model, target_id):
        if model is Item:
            return items.get(target_id)
        if model is ItemType:
            return item_types.get(target_id)
        if model is LifecycleState:
            return states.get(target_id)
        if model is ItemVersion:
            return versions.get(target_id)
        return None

    session.get.side_effect = _get
    session.query.return_value = _Query(query_result)
    return session


def _settings(disabled=False):
    return SimpleNamespace(SUSPENDED_GUARD_DISABLED=disabled)


def test_suspended_guard_enabled_by_default() -> None:
    service = SuspendedGuardService(MagicMock(), settings=_settings(False))

    assert service.is_enabled() is True


def test_suspended_guard_can_be_disabled_via_settings() -> None:
    service = SuspendedGuardService(MagicMock(), settings=_settings(True))

    assert service.is_enabled() is False


def test_suspended_guard_can_be_disabled_via_tenant_org_config() -> None:
    plugin_service = MagicMock()
    plugin_service.get_config.side_effect = [SimpleNamespace(config={"disabled": True}), None]

    with patch(
        "yuantus.meta_engine.services.suspended_guard.PluginConfigService",
        return_value=plugin_service,
    ), patch(
        "yuantus.meta_engine.services.suspended_guard.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ):
        service = SuspendedGuardService(MagicMock(), settings=_settings(False))
        assert service.is_enabled() is False


def test_suspended_guard_can_be_disabled_via_tenant_default_config() -> None:
    plugin_service = MagicMock()
    plugin_service.get_config.side_effect = [None, SimpleNamespace(config={"disabled": True})]

    with patch(
        "yuantus.meta_engine.services.suspended_guard.PluginConfigService",
        return_value=plugin_service,
    ), patch(
        "yuantus.meta_engine.services.suspended_guard.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ):
        service = SuspendedGuardService(MagicMock(), settings=_settings(False))
        assert service.is_enabled() is False


def test_assert_not_suspended_rejects_item_current_state_flag() -> None:
    state = LifecycleState(id="state-suspended", name="Suspended", is_suspended=True)
    item = Item(id="item-1", item_type_id="Part", current_state="state-suspended")
    item_type = ItemType(id="Part", lifecycle_map_id="lc-part")
    session = _session_for(
        items={"item-1": item},
        item_types={"Part": item_type},
        states={"state-suspended": state},
    )

    with pytest.raises(SuspendedStateError) as exc_info:
        SuspendedGuardService(session, settings=_settings(False)).assert_not_suspended(
            "item-1", context="bom_child"
        )

    assert exc_info.value.to_detail()["error"] == "SUSPENDED_STATE"
    assert exc_info.value.reason == "target_suspended"


def test_assert_not_suspended_uses_item_type_fallback_for_state_name() -> None:
    state = LifecycleState(id="state-suspended", name="Suspended", is_suspended=True)
    item = Item(id="item-1", item_type_id="Part", current_state=None, state="Suspended")
    item_type = ItemType(id="Part", lifecycle_map_id="lc-part")
    session = _session_for(
        items={"item-1": item},
        item_types={"Part": item_type},
        query_result=state,
    )

    with pytest.raises(SuspendedStateError):
        SuspendedGuardService(session, settings=_settings(False)).assert_not_suspended(
            "item-1", context="substitute"
        )

    session.get.assert_any_call(ItemType, "Part")


def test_effectivity_relationship_checks_related_item_state() -> None:
    state = LifecycleState(id="state-suspended", name="Suspended", is_suspended=True)
    rel = Item(id="rel-1", related_id="child-1", item_type_id="Part BOM")
    child = Item(id="child-1", item_type_id="Part", current_state="state-suspended")
    item_type = ItemType(id="Part", lifecycle_map_id="lc-part")
    session = _session_for(
        items={"rel-1": rel, "child-1": child},
        item_types={"Part": item_type},
        states={"state-suspended": state},
    )

    with pytest.raises(SuspendedStateError):
        SuspendedGuardService(session, settings=_settings(False)).assert_not_suspended(
            "rel-1", context="effectivity"
        )


def test_effectivity_version_checks_version_state_fallback() -> None:
    state = LifecycleState(id="state-suspended", name="Suspended", is_suspended=True)
    item = Item(id="item-1", item_type_id="Part", current_state=None, state="Released")
    item_type = ItemType(id="Part", lifecycle_map_id="lc-part")
    version = ItemVersion(id="ver-1", item_id="item-1", state="Suspended")
    session = _session_for(
        items={"item-1": item},
        item_types={"Part": item_type},
        versions={"ver-1": version},
        query_result=state,
    )

    with pytest.raises(SuspendedStateError) as exc_info:
        SuspendedGuardService(session, settings=_settings(False)).assert_not_suspended(
            "ver-1", context="effectivity"
        )

    assert exc_info.value.reason == "current_version_suspended"
    assert exc_info.value.target_id == "ver-1"


def test_effectivity_version_reports_version_id_when_parent_item_suspended() -> None:
    state = LifecycleState(id="state-suspended", name="Suspended", is_suspended=True)
    item = Item(id="item-1", item_type_id="Part", current_state="state-suspended")
    item_type = ItemType(id="Part", lifecycle_map_id="lc-part")
    version = ItemVersion(id="ver-1", item_id="item-1", state="Released")
    session = _session_for(
        items={"item-1": item},
        item_types={"Part": item_type},
        states={"state-suspended": state},
        versions={"ver-1": version},
    )

    with pytest.raises(SuspendedStateError) as exc_info:
        SuspendedGuardService(session, settings=_settings(False)).assert_not_suspended(
            "ver-1", context="effectivity"
        )

    assert exc_info.value.reason == "current_version_suspended"
    assert exc_info.value.target_id == "ver-1"


def test_non_suspended_item_passes() -> None:
    state = LifecycleState(id="state-released", name="Released", is_suspended=False)
    item = Item(id="item-1", item_type_id="Part", current_state="state-released")
    item_type = ItemType(id="Part", lifecycle_map_id="lc-part")
    session = _session_for(
        items={"item-1": item},
        item_types={"Part": item_type},
        states={"state-released": state},
    )

    SuspendedGuardService(session, settings=_settings(False)).assert_not_suspended(
        "item-1", context="bom_child"
    )
