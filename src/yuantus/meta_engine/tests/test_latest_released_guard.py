from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.latest_released_guard import (
    LatestReleasedGuardService,
    NotLatestReleasedError,
)
from yuantus.meta_engine.version.models import ItemVersion


def _session_for(*, items: dict[str, Item], versions: dict[str, ItemVersion]):
    session = MagicMock()

    def _get(model, target_id):
        if model is Item:
            return items.get(target_id)
        if model is ItemVersion:
            return versions.get(target_id)
        return None

    session.get.side_effect = _get
    return session


def test_latest_released_item_passes() -> None:
    item = Item(id="item-1", is_current=True, current_version_id="ver-1")
    version = ItemVersion(id="ver-1", item_id="item-1", is_current=True, is_released=True)
    session = _session_for(items={"item-1": item}, versions={"ver-1": version})

    LatestReleasedGuardService(
        session,
        settings=SimpleNamespace(LATEST_RELEASED_GUARD_DISABLED=False),
    ).assert_latest_released("item-1", context="bom_child")


def test_non_current_item_is_rejected() -> None:
    item = Item(id="item-1", is_current=False, current_version_id="ver-1")
    version = ItemVersion(id="ver-1", item_id="item-1", is_current=True, is_released=True)
    session = _session_for(items={"item-1": item}, versions={"ver-1": version})

    with pytest.raises(NotLatestReleasedError, match="latest current item/version"):
        LatestReleasedGuardService(
            session,
            settings=SimpleNamespace(LATEST_RELEASED_GUARD_DISABLED=False),
        ).assert_latest_released("item-1", context="bom_child")


def test_unreleased_current_version_is_rejected() -> None:
    item = Item(id="item-1", is_current=True, current_version_id="ver-1")
    version = ItemVersion(id="ver-1", item_id="item-1", is_current=True, is_released=False)
    session = _session_for(items={"item-1": item}, versions={"ver-1": version})

    with pytest.raises(NotLatestReleasedError, match="not released"):
        LatestReleasedGuardService(
            session,
            settings=SimpleNamespace(LATEST_RELEASED_GUARD_DISABLED=False),
        ).assert_latest_released("item-1", context="substitute")


def test_effectivity_on_relationship_checks_related_item() -> None:
    child = Item(id="child-1", is_current=True, current_version_id="ver-1")
    rel = Item(
        id="rel-1",
        is_current=True,
        current_version_id=None,
        source_id="parent-1",
        related_id="child-1",
    )
    version = ItemVersion(id="ver-1", item_id="child-1", is_current=True, is_released=True)
    session = _session_for(
        items={"rel-1": rel, "child-1": child},
        versions={"ver-1": version},
    )

    LatestReleasedGuardService(
        session,
        settings=SimpleNamespace(LATEST_RELEASED_GUARD_DISABLED=False),
    ).assert_latest_released("rel-1", context="effectivity")


def test_effectivity_on_stale_relationship_is_rejected_even_if_related_item_is_current() -> None:
    child = Item(id="child-1", is_current=True, current_version_id="ver-1")
    rel = Item(
        id="rel-1",
        is_current=False,
        current_version_id=None,
        source_id="parent-1",
        related_id="child-1",
    )
    version = ItemVersion(id="ver-1", item_id="child-1", is_current=True, is_released=True)
    session = _session_for(
        items={"rel-1": rel, "child-1": child},
        versions={"ver-1": version},
    )

    with pytest.raises(NotLatestReleasedError, match="latest current item/version"):
        LatestReleasedGuardService(
            session,
            settings=SimpleNamespace(LATEST_RELEASED_GUARD_DISABLED=False),
        ).assert_latest_released("rel-1", context="effectivity")


def test_guard_can_be_disabled_via_settings() -> None:
    session = MagicMock()
    service = LatestReleasedGuardService(
        session,
        settings=SimpleNamespace(LATEST_RELEASED_GUARD_DISABLED=True),
    )

    assert service.is_enabled() is False


def test_guard_can_be_disabled_via_scoped_plugin_config() -> None:
    session = MagicMock()
    plugin_service = MagicMock()
    plugin_service.get_config.side_effect = [SimpleNamespace(config={"disabled": True}), None]

    with patch(
        "yuantus.meta_engine.services.latest_released_guard.PluginConfigService",
        return_value=plugin_service,
    ), patch(
        "yuantus.meta_engine.services.latest_released_guard.get_request_context",
        return_value=SimpleNamespace(tenant_id="tenant-1", org_id="org-1"),
    ):
        service = LatestReleasedGuardService(
            session,
            settings=SimpleNamespace(LATEST_RELEASED_GUARD_DISABLED=False),
        )
        assert service.is_enabled() is False
