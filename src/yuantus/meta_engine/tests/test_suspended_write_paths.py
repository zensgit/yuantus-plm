from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.effectivity_service import EffectivityService
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.substitute_service import SubstituteService
from yuantus.meta_engine.services.suspended_guard import SuspendedStateError


def test_bom_add_child_invokes_suspended_guard_after_latest_released() -> None:
    session = MagicMock()
    parent = Item(id="parent-1", permission_id="perm-1")
    child = Item(id="child-1")
    session.get.side_effect = lambda model, item_id: {
        "parent-1": parent,
        "child-1": child,
    }.get(item_id)

    service = BOMService(session)
    service.detect_cycle_with_path = MagicMock(return_value={"has_cycle": False, "cycle_path": None})
    service.get_bom_line_by_parent_child = MagicMock(return_value=None)

    with patch("yuantus.meta_engine.services.bom_service.assert_latest_released") as latest, patch(
        "yuantus.meta_engine.services.bom_service.assert_not_suspended"
    ) as suspended:
        service.add_child(parent_id="parent-1", child_id="child-1", user_id=1)

    latest.assert_called_once_with(session, "child-1", context="bom_child")
    suspended.assert_called_once_with(session, "child-1", context="bom_child")


def test_bom_add_child_does_not_create_relationship_when_suspended() -> None:
    session = MagicMock()
    parent = Item(id="parent-1", permission_id="perm-1")
    child = Item(id="child-1")
    session.get.side_effect = lambda model, item_id: {
        "parent-1": parent,
        "child-1": child,
    }.get(item_id)

    service = BOMService(session)

    with patch("yuantus.meta_engine.services.bom_service.assert_latest_released"), patch(
        "yuantus.meta_engine.services.bom_service.assert_not_suspended",
        side_effect=SuspendedStateError(reason="target_suspended", target_id="child-1"),
    ):
        with pytest.raises(SuspendedStateError):
            service.add_child(parent_id="parent-1", child_id="child-1", user_id=1)

    session.add.assert_not_called()


def test_latest_released_guard_runs_before_suspended_guard() -> None:
    session = MagicMock()
    parent = Item(id="parent-1", permission_id="perm-1")
    child = Item(id="child-1")
    session.get.side_effect = lambda model, item_id: {
        "parent-1": parent,
        "child-1": child,
    }.get(item_id)
    service = BOMService(session)

    with patch(
        "yuantus.meta_engine.services.bom_service.assert_latest_released",
        side_effect=NotLatestReleasedError(reason="not_latest_released", target_id="child-1"),
    ), patch("yuantus.meta_engine.services.bom_service.assert_not_suspended") as suspended:
        with pytest.raises(NotLatestReleasedError):
            service.add_child(parent_id="parent-1", child_id="child-1", user_id=1)

    suspended.assert_not_called()


def test_substitute_add_invokes_suspended_guard() -> None:
    session = MagicMock()
    bom_line = Item(id="bom-1", item_type_id="Part BOM")
    substitute = Item(id="sub-1")
    session.get.side_effect = lambda model, item_id: {
        "bom-1": bom_line,
        "sub-1": substitute,
    }.get(item_id)
    query = MagicMock()
    query.filter.return_value.first.return_value = None
    session.query.return_value = query

    service = SubstituteService(session)
    service.ensure_substitute_item_type = MagicMock()
    service.permission_service = MagicMock()

    with patch(
        "yuantus.meta_engine.services.substitute_service.assert_latest_released"
    ) as latest, patch(
        "yuantus.meta_engine.services.substitute_service.assert_not_suspended"
    ) as suspended:
        service.add_substitute("bom-1", "sub-1", user_id=1)

    latest.assert_called_once_with(session, "sub-1", context="substitute")
    suspended.assert_called_once_with(session, "sub-1", context="substitute")


def test_substitute_add_does_not_create_relationship_when_suspended() -> None:
    session = MagicMock()
    bom_line = Item(id="bom-1", item_type_id="Part BOM")
    substitute = Item(id="sub-1")
    session.get.side_effect = lambda model, item_id: {
        "bom-1": bom_line,
        "sub-1": substitute,
    }.get(item_id)

    service = SubstituteService(session)
    service.ensure_substitute_item_type = MagicMock()
    service.permission_service = MagicMock()

    with patch("yuantus.meta_engine.services.substitute_service.assert_latest_released"), patch(
        "yuantus.meta_engine.services.substitute_service.assert_not_suspended",
        side_effect=SuspendedStateError(reason="target_suspended", target_id="sub-1"),
    ):
        with pytest.raises(SuspendedStateError):
            service.add_substitute("bom-1", "sub-1", user_id=1)

    session.add.assert_not_called()


def test_effectivity_create_invokes_suspended_guard_for_both_targets() -> None:
    session = MagicMock()
    service = EffectivityService(session)

    with patch(
        "yuantus.meta_engine.services.effectivity_service.assert_latest_released"
    ), patch(
        "yuantus.meta_engine.services.effectivity_service.assert_not_suspended"
    ) as suspended:
        service.create_effectivity(
            item_id="item-1",
            version_id="ver-1",
            effectivity_type="Date",
            start_date=None,
            end_date=None,
        )

    assert suspended.call_args_list == [
        call(session, "item-1", context="effectivity"),
        call(session, "ver-1", context="effectivity"),
    ]


def test_effectivity_create_does_not_create_record_when_suspended() -> None:
    session = MagicMock()
    service = EffectivityService(session)

    with patch("yuantus.meta_engine.services.effectivity_service.assert_latest_released"), patch(
        "yuantus.meta_engine.services.effectivity_service.assert_not_suspended",
        side_effect=SuspendedStateError(reason="target_suspended", target_id="item-1"),
    ):
        with pytest.raises(SuspendedStateError):
            service.create_effectivity(item_id="item-1")

    session.add.assert_not_called()
