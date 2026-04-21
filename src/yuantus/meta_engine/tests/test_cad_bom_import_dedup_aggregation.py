from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.locale.service import resolve_localized_property
from yuantus.meta_engine.services.cad_bom_import_service import (
    CadBomImportService,
    _normalize_uom,
    _normalize_localized_text_map,
    _refdes_tokens,
    _join_refdes_tokens,
)
from yuantus.models.base import Base
from yuantus.models import user as _user  # noqa: F401 — registers 'users' table for effectivity FK

import_all_models()


# --- _normalize_uom unit tests ---


def test_normalize_uom_empty_uses_default() -> None:
    assert _normalize_uom(None) == "EA"
    assert _normalize_uom("") == "EA"
    assert _normalize_uom("   ") == "EA"


def test_normalize_uom_strips_and_uppercases() -> None:
    assert _normalize_uom("mm") == "MM"
    assert _normalize_uom(" mm ") == "MM"
    assert _normalize_uom("MM") == "MM"
    assert _normalize_uom(" Each ") == "EACH"
    assert _normalize_uom("kg") == "KG"


def test_normalize_uom_custom_default() -> None:
    assert _normalize_uom(None, default="UN") == "UN"
    assert _normalize_uom("", default="UN") == "UN"
    assert _normalize_uom("mm", default="UN") == "MM"


# --- localized text helper tests ---


def test_normalize_localized_text_map_filters_empty_values() -> None:
    assert _normalize_localized_text_map(None) is None
    assert _normalize_localized_text_map("Bolt") is None
    assert _normalize_localized_text_map({"zh_CN": " 内六角螺栓 ", "en_US": ""}) == {
        "zh_CN": "内六角螺栓"
    }
    assert _normalize_localized_text_map({"zh_CN": None, "en_US": "  "}) is None


# --- _refdes_tokens / _join_refdes_tokens unit tests ---


def test_refdes_tokens_none_and_empty() -> None:
    assert _refdes_tokens(None) == []
    assert _refdes_tokens("") == []
    assert _refdes_tokens("   ") == []


def test_refdes_tokens_from_comma_separated_string() -> None:
    assert _refdes_tokens("R1,R2,R3") == ["R1", "R2", "R3"]
    assert _refdes_tokens(" R1 , R2 , R3 ") == ["R1", "R2", "R3"]
    assert _refdes_tokens("R1,,R2,") == ["R1", "R2"]


def test_refdes_tokens_from_list_preserves_input_order() -> None:
    assert _refdes_tokens(["R3", "R1", "R2"]) == ["R3", "R1", "R2"]
    assert _refdes_tokens(("R1", "", "R2", None, "  ")) == ["R1", "R2"]


def test_join_refdes_tokens_natural_sorts_and_deduplicates() -> None:
    assert _join_refdes_tokens(["R2", "R1", "R3", "R1"]) == "R1,R2,R3"
    assert _join_refdes_tokens({"R1", "R2"}) == "R1,R2"
    assert _join_refdes_tokens([]) is None
    assert _join_refdes_tokens(None) is None
    assert _join_refdes_tokens(["  ", None, ""]) is None


def test_join_refdes_tokens_orders_numeric_chunks_naturally() -> None:
    assert _join_refdes_tokens(["R10", "R2", "R1"]) == "R1,R2,R10"
    assert _join_refdes_tokens(["C10", "R1", "C2", "R10"]) == "C2,C10,R1,R10"


# --- import_bom aggregation integration tests (mock bom_service) ---


def _make_service_and_add_child_mock():
    """
    Build a CadBomImportService with a session mock that:
    - returns a stubbed root Item for session.get(Item, root_item_id)
    - returns a stubbed ItemType for session.get(ItemType, 'Part') with item_number property
    - returns None for _find_existing query chain (forces new item creation per node)
    - no-ops on session.add / session.flush
    And replaces bom_service with a MagicMock so add_child calls can be captured.
    """
    session = MagicMock()

    root_item = SimpleNamespace(id="root-item-id", permission_id="perm-default")
    part_type = SimpleNamespace(
        id="Part",
        properties=[
            SimpleNamespace(name="item_number", is_cad_synced=False, ui_options={}),
            SimpleNamespace(name="name", is_cad_synced=False, ui_options={}),
            SimpleNamespace(name="description", is_cad_synced=False, ui_options={}),
        ],
    )

    def get_side_effect(model, id_):
        if id_ == "root-item-id":
            return root_item
        if id_ == "Part":
            return part_type
        return None

    session.get.side_effect = get_side_effect

    query_chain = MagicMock()
    query_chain.filter.return_value.filter.return_value.first.return_value = None
    session.query.return_value = query_chain

    service = CadBomImportService(session)
    service.bom_service = MagicMock()
    service.bom_service.add_child = MagicMock(return_value={"ok": True})
    return service, session, service.bom_service.add_child


def _created_item_properties(session, item_number: str):
    for call in session.add.call_args_list:
        item = call.args[0]
        if isinstance(item, Item) and (item.properties or {}).get("item_number") == item_number:
            return item.properties
    raise AssertionError(f"created item not found: {item_number}")


def _payload(edges, *, nodes=None, root="root"):
    default_nodes = nodes or [
        {"id": "root", "item_number": "ROOT-001"},
        {"id": "c1", "item_number": "PART-A"},
        {"id": "c2", "item_number": "PART-B"},
    ]
    return {"nodes": default_nodes, "edges": edges, "root": root}


def test_import_bom_aggregates_duplicate_edges_same_uom() -> None:
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [
            {"parent": "root", "child": "c1", "quantity": 2, "uom": "EA"},
            {"parent": "root", "child": "c1", "quantity": 3, "uom": "EA"},
            {"parent": "root", "child": "c2", "quantity": 1, "uom": "EA"},
        ]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["ok"] is True
    assert result["dedup_aggregated"] == 1
    assert result["created_lines"] == 2
    assert result["skipped_lines"] == 0
    assert add_child.call_count == 2

    quantities = sorted(c.kwargs["quantity"] for c in add_child.call_args_list)
    assert quantities == [1, 5]
    uoms = {c.kwargs["uom"] for c in add_child.call_args_list}
    assert uoms == {"EA"}


def test_import_bom_preserves_direct_description_i18n_map() -> None:
    service, session, _ = _make_service_and_add_child_mock()
    payload = _payload(
        [{"parent": "root", "child": "c1", "quantity": 1, "uom": "EA"}],
        nodes=[
            {"id": "root", "item_number": "ROOT-001"},
            {
                "id": "c1",
                "item_number": "PART-I18N",
                "description": {
                    "zh_CN": "内六角螺栓",
                    "en_US": "Hex bolt",
                    "fr_FR": "  ",
                },
            },
        ],
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["created_items"] == 1
    props = _created_item_properties(session, "PART-I18N")
    assert props["description"] == "Hex bolt"
    assert props["description_i18n"] == {
        "zh_CN": "内六角螺栓",
        "en_US": "Hex bolt",
    }
    resolved = resolve_localized_property(props, "description", lang="zh_CN")
    assert resolved["value"] == "内六角螺栓"
    assert resolved["source"] == "properties_i18n"


def test_import_bom_preserves_nested_description_i18n_without_changing_scalar() -> None:
    service, session, _ = _make_service_and_add_child_mock()
    payload = _payload(
        [{"parent": "root", "child": "c1", "quantity": 1, "uom": "EA"}],
        nodes=[
            {"id": "root", "item_number": "ROOT-001"},
            {
                "id": "c1",
                "item_number": "PART-NESTED-I18N",
                "description": "Hex bolt",
                "i18n": {"description": {"zh_CN": "内六角螺栓"}},
            },
        ],
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["created_items"] == 1
    props = _created_item_properties(session, "PART-NESTED-I18N")
    assert props["description"] == "Hex bolt"
    assert props["description_i18n"] == {"zh_CN": "内六角螺栓"}


def test_import_bom_preserves_name_i18n_map() -> None:
    service, session, _ = _make_service_and_add_child_mock()
    payload = _payload(
        [{"parent": "root", "child": "c1", "quantity": 1, "uom": "EA"}],
        nodes=[
            {"id": "root", "item_number": "ROOT-001"},
            {
                "id": "c1",
                "item_number": "PART-NAME-I18N",
                "name_i18n": {"zh_CN": "支架", "en_US": "Bracket"},
            },
        ],
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["created_items"] == 1
    props = _created_item_properties(session, "PART-NAME-I18N")
    assert props["name"] == "Bracket"
    assert props["name_i18n"] == {"zh_CN": "支架", "en_US": "Bracket"}
    resolved = resolve_localized_property(props, "name", lang="zh_CN")
    assert resolved["value"] == "支架"


def test_import_bom_scalar_description_does_not_create_i18n_sidecar() -> None:
    service, session, _ = _make_service_and_add_child_mock()
    payload = _payload(
        [{"parent": "root", "child": "c1", "quantity": 1, "uom": "EA"}],
        nodes=[
            {"id": "root", "item_number": "ROOT-001"},
            {
                "id": "c1",
                "item_number": "PART-SCALAR",
                "description": "Plain CAD description",
            },
        ],
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["created_items"] == 1
    props = _created_item_properties(session, "PART-SCALAR")
    assert props["description"] == "Plain CAD description"
    assert "description_i18n" not in props


def test_import_bom_normalizes_uom_case_and_whitespace() -> None:
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [
            {"parent": "root", "child": "c1", "quantity": 2, "uom": "mm"},
            {"parent": "root", "child": "c1", "quantity": 3, "uom": " MM "},
            {"parent": "root", "child": "c1", "quantity": 5, "uom": "mM"},
        ]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["dedup_aggregated"] == 2
    assert result["created_lines"] == 1
    assert add_child.call_count == 1
    call_kw = add_child.call_args_list[0].kwargs
    assert call_kw["uom"] == "MM"
    assert call_kw["quantity"] == 10


def test_import_bom_missing_uom_defaults_to_EA_and_merges_with_explicit_EA() -> None:
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [
            {"parent": "root", "child": "c1", "quantity": 2},  # no uom
            {"parent": "root", "child": "c1", "quantity": 3, "uom": ""},  # empty uom
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA"},
        ]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["dedup_aggregated"] == 2
    assert result["created_lines"] == 1
    call_kw = add_child.call_args_list[0].kwargs
    assert call_kw["uom"] == "EA"
    assert call_kw["quantity"] == 6


def test_import_bom_preserves_first_non_empty_find_num() -> None:
    """find_num stays first-non-empty (not merged like refdes)."""
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "find_num": None},
            {"parent": "root", "child": "c1", "quantity": 2, "uom": "EA", "find_num": "10"},
            {"parent": "root", "child": "c1", "quantity": 3, "uom": "EA", "find_num": "20"},
        ]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["dedup_aggregated"] == 2
    assert result["created_lines"] == 1
    call_kw = add_child.call_args_list[0].kwargs
    assert call_kw["find_num"] == "10"
    assert call_kw["quantity"] == 6


def test_import_bom_merges_refdes_tokens_across_duplicates_deduped_and_sorted() -> None:
    """refdes tokens accumulate across duplicate edges, deduped, lexicographic-sorted."""
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "refdes": "R3"},
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "refdes": "R1,R2"},
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "refdes": "R1"},  # dup R1
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "refdes": None},
        ]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["dedup_aggregated"] == 3
    assert result["created_lines"] == 1
    call_kw = add_child.call_args_list[0].kwargs
    assert call_kw["refdes"] == "R1,R2,R3"
    assert call_kw["quantity"] == 4


def test_import_bom_sorts_single_edge_comma_separated_refdes() -> None:
    """Single edge with comma-separated refdes still gets natural-sorted + deduped."""
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [{"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "refdes": "R10,R1,R2,R1"}]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["created_lines"] == 1
    call_kw = add_child.call_args_list[0].kwargs
    assert call_kw["refdes"] == "R1,R2,R10"


def test_import_bom_refdes_all_empty_yields_none() -> None:
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "refdes": None},
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA", "refdes": ""},
            {"parent": "root", "child": "c1", "quantity": 1, "uom": "EA"},
        ]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["dedup_aggregated"] == 2
    assert result["created_lines"] == 1
    assert add_child.call_args_list[0].kwargs["refdes"] is None


def test_import_bom_no_duplicates_passthrough() -> None:
    service, _, add_child = _make_service_and_add_child_mock()
    payload = _payload(
        [
            {"parent": "root", "child": "c1", "quantity": 2, "uom": "EA"},
            {"parent": "root", "child": "c2", "quantity": 5, "uom": "KG"},
        ]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["dedup_aggregated"] == 0
    assert result["created_lines"] == 2
    assert result["skipped_lines"] == 0
    assert add_child.call_count == 2


def test_import_bom_multi_parent_same_child_is_not_cross_parent_aggregated() -> None:
    """Same child item under different parents must produce separate BOM lines."""
    service, _, add_child = _make_service_and_add_child_mock()
    nodes = [
        {"id": "root", "item_number": "ROOT-001"},
        {"id": "subA", "item_number": "SUB-A"},
        {"id": "subB", "item_number": "SUB-B"},
        {"id": "bolt", "item_number": "BOLT"},
    ]
    payload = _payload(
        nodes=nodes,
        edges=[
            {"parent": "root", "child": "subA", "quantity": 1, "uom": "EA"},
            {"parent": "root", "child": "subB", "quantity": 1, "uom": "EA"},
            {"parent": "subA", "child": "bolt", "quantity": 4, "uom": "EA"},
            {"parent": "subB", "child": "bolt", "quantity": 4, "uom": "EA"},
        ],
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert result["dedup_aggregated"] == 0
    assert result["created_lines"] == 4
    assert add_child.call_count == 4


def test_import_bom_result_schema_always_includes_dedup_aggregated() -> None:
    service, _, _ = _make_service_and_add_child_mock()
    payload = _payload(
        [{"parent": "root", "child": "c1", "quantity": 1, "uom": "EA"}]
    )

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload=payload, user_id=1
    )

    assert "dedup_aggregated" in result
    assert result["dedup_aggregated"] == 0


def test_import_bom_empty_payload_still_returns_consistent_schema() -> None:
    service, _, _ = _make_service_and_add_child_mock()

    result = service.import_bom(
        root_item_id="root-item-id", bom_payload={}, user_id=1
    )

    assert result["ok"] is True
    assert result["created_items"] == 0
    assert result["created_lines"] == 0
    # empty_bom shortcut intentionally omits dedup_aggregated (no commit phase ran);
    # this test pins that behavior so callers know to default-to-0 on 'note' shortcuts.
    assert result.get("note") == "empty_bom"


# --- Real-session integration test (SQLite in-memory via tmp_path) ---


def test_import_bom_real_session_different_uom_creates_two_bom_lines(
    tmp_path: Path,
) -> None:
    """
    Real BOMService integration: two edges share (parent, child) but differ in uom.

    Phase 1 aggregation correctly keeps two separate keys (dedup_aggregated=0).
    Phase 2 commit now uses BOMService's UOM-aware duplicate guard, so both
    rows can be written as distinct BOM relationship lines.
    """
    db_path = tmp_path / "cad_bom_import_dedup.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()

    try:
        part_type = ItemType(
            id="Part",
            label="Part",
            is_relationship=False,
            is_versionable=True,
            revision_scheme="A-Z",
        )
        bom_type = ItemType(
            id="Part BOM",
            label="Part BOM",
            is_relationship=True,
            source_item_type_id="Part",
            related_item_type_id="Part",
        )
        root_item = Item(
            id="root-item-id",
            item_type_id="Part",
            config_id="config-root",
            generation=1,
            is_current=True,
            state="Active",
            properties={"item_number": "ROOT-001", "name": "Root"},
            permission_id=None,
        )
        session.add_all([part_type, bom_type, root_item])
        session.commit()

        service = CadBomImportService(session)
        payload = {
            "nodes": [
                {"id": "root", "item_number": "ROOT-001"},
                {"id": "c1", "item_number": "PART-A"},
            ],
            "edges": [
                {"parent": "root", "child": "c1", "quantity": 2, "uom": "EA"},
                {"parent": "root", "child": "c1", "quantity": 100, "uom": "MM"},
            ],
            "root": "root",
        }

        # The real BOMService.add_child calls the latest-released + not-suspended guards;
        # patch them to no-ops so this test isolates the uom-duplicate behavior.
        with patch(
            "yuantus.meta_engine.services.bom_service.assert_latest_released"
        ), patch(
            "yuantus.meta_engine.services.bom_service.assert_not_suspended"
        ):
            result = service.import_bom(
                root_item_id="root-item-id", bom_payload=payload, user_id=1
            )

        assert result["ok"] is True
        # Phase 1 preserves the uom distinction: no cross-uom aggregation.
        assert result["dedup_aggregated"] == 0
        # Phase 2 persists both UOM-specific BOM lines.
        assert result["created_lines"] == 2, result
        assert result["skipped_lines"] == 0, result
        assert result["errors"] == []

        lines = (
            session.query(Item)
            .filter(Item.source_id == "root-item-id", Item.item_type_id == "Part BOM")
            .all()
        )
        assert sorted((line.properties or {}).get("uom") for line in lines) == ["EA", "MM"]
    finally:
        session.close()
        engine.dispose()
