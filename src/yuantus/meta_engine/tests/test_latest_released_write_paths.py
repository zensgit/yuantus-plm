from __future__ import annotations

from unittest.mock import call
from unittest.mock import MagicMock, patch

import pytest

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.meta_engine.services.effectivity_service import EffectivityService
from yuantus.meta_engine.services.latest_released_guard import NotLatestReleasedError
from yuantus.meta_engine.services.substitute_service import SubstituteService


def test_bom_add_child_invokes_latest_released_guard() -> None:
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

    with patch("yuantus.meta_engine.services.bom_service.assert_latest_released") as guard, patch(
        "yuantus.meta_engine.services.bom_service.assert_not_suspended"
    ):
        service.add_child(parent_id="parent-1", child_id="child-1", user_id=1)

    guard.assert_called_once_with(session, "child-1", context="bom_child")


def test_substitute_add_invokes_latest_released_guard() -> None:
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
    ) as guard, patch(
        "yuantus.meta_engine.services.substitute_service.assert_not_suspended"
    ):
        service.add_substitute("bom-1", "sub-1", user_id=1)

    guard.assert_called_once_with(session, "sub-1", context="substitute")


def test_effectivity_create_invokes_latest_released_guard() -> None:
    session = MagicMock()
    service = EffectivityService(session)

    with patch(
        "yuantus.meta_engine.services.effectivity_service.assert_latest_released"
    ) as guard, patch(
        "yuantus.meta_engine.services.effectivity_service.assert_not_suspended"
    ):
        service.create_effectivity(item_id="item-1", effectivity_type="Date", start_date=None, end_date=None)

    guard.assert_called_once_with(session, "item-1", context="effectivity")


def test_effectivity_create_checks_both_item_and_version_targets() -> None:
    session = MagicMock()
    service = EffectivityService(session)

    with patch(
        "yuantus.meta_engine.services.effectivity_service.assert_latest_released"
    ) as guard, patch(
        "yuantus.meta_engine.services.effectivity_service.assert_not_suspended"
    ):
        service.create_effectivity(
            item_id="item-1",
            version_id="ver-2",
            effectivity_type="Date",
            start_date=None,
            end_date=None,
        )

    assert guard.call_args_list == [
        call(session, "item-1", context="effectivity"),
        call(session, "ver-2", context="effectivity"),
    ]


def test_effectivity_create_rejects_when_second_target_is_stale() -> None:
    session = MagicMock()
    service = EffectivityService(session)

    with patch(
        "yuantus.meta_engine.services.effectivity_service.assert_latest_released",
        side_effect=[
            None,
            NotLatestReleasedError(
                reason="not_latest_released",
                target_id="ver-2",
            ),
        ],
    ), patch("yuantus.meta_engine.services.effectivity_service.assert_not_suspended"):
        with pytest.raises(NotLatestReleasedError, match="latest current item/version"):
            service.create_effectivity(
                item_id="item-1",
                version_id="ver-2",
                effectivity_type="Date",
                start_date=None,
                end_date=None,
            )
