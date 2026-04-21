from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.bom_service import BOMService
from yuantus.models.base import Base
from yuantus.models import user as _user  # noqa: F401 - registers users table

import_all_models()


@pytest.fixture()
def bom_service(tmp_path: Path):
    db_path = tmp_path / "bom_uom_duplicate_guard.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    session.add_all(
        [
            ItemType(
                id="Part",
                label="Part",
                is_relationship=False,
                is_versionable=True,
                revision_scheme="A-Z",
            ),
            ItemType(
                id="Part BOM",
                label="Part BOM",
                is_relationship=True,
                source_item_type_id="Part",
                related_item_type_id="Part",
            ),
            Item(
                id="parent-1",
                item_type_id="Part",
                config_id="cfg-parent",
                generation=1,
                is_current=True,
                state="Active",
                properties={"item_number": "PARENT-1"},
            ),
            Item(
                id="child-1",
                item_type_id="Part",
                config_id="cfg-child",
                generation=1,
                is_current=True,
                state="Active",
                properties={"item_number": "CHILD-1"},
            ),
        ]
    )
    session.commit()

    try:
        with patch(
            "yuantus.meta_engine.services.bom_service.assert_latest_released"
        ), patch("yuantus.meta_engine.services.bom_service.assert_not_suspended"):
            yield BOMService(session)
    finally:
        session.close()
        engine.dispose()


def test_add_child_allows_same_parent_child_when_uom_differs(bom_service: BOMService) -> None:
    first = bom_service.add_child(
        parent_id="parent-1",
        child_id="child-1",
        quantity=2,
        uom="EA",
    )
    second = bom_service.add_child(
        parent_id="parent-1",
        child_id="child-1",
        quantity=100,
        uom="MM",
    )

    assert first["relationship_id"] != second["relationship_id"]
    lines = bom_service.get_bom_lines_by_parent_child("parent-1", "child-1")
    assert sorted((line.properties or {}).get("uom") for line in lines) == ["EA", "MM"]


def test_add_child_rejects_same_normalized_uom_duplicate(bom_service: BOMService) -> None:
    bom_service.add_child(
        parent_id="parent-1",
        child_id="child-1",
        quantity=2,
        uom="ea",
    )

    with pytest.raises(ValueError, match=r"uom=EA"):
        bom_service.add_child(
            parent_id="parent-1",
            child_id="child-1",
            quantity=3,
            uom=" EA ",
        )

    lines = bom_service.get_bom_lines_by_parent_child("parent-1", "child-1")
    assert len(lines) == 1
    assert lines[0].properties["uom"] == "EA"


def test_get_bom_line_by_parent_child_disambiguates_by_uom(bom_service: BOMService) -> None:
    ea = bom_service.add_child(parent_id="parent-1", child_id="child-1", uom="EA")
    mm = bom_service.add_child(parent_id="parent-1", child_id="child-1", uom="MM")

    assert (
        bom_service.get_bom_line_by_parent_child("parent-1", "child-1", uom="ea").id
        == ea["relationship_id"]
    )
    assert (
        bom_service.get_bom_line_by_parent_child("parent-1", "child-1", uom=" mm ").id
        == mm["relationship_id"]
    )


def test_remove_child_requires_uom_when_multiple_lines_exist(bom_service: BOMService) -> None:
    bom_service.add_child(parent_id="parent-1", child_id="child-1", uom="EA")
    bom_service.add_child(parent_id="parent-1", child_id="child-1", uom="MM")

    with pytest.raises(ValueError, match="specify uom"):
        bom_service.remove_child(parent_id="parent-1", child_id="child-1")


def test_remove_child_with_uom_removes_selected_line(bom_service: BOMService) -> None:
    ea = bom_service.add_child(parent_id="parent-1", child_id="child-1", uom="EA")
    mm = bom_service.add_child(parent_id="parent-1", child_id="child-1", uom="MM")

    removed = bom_service.remove_child(parent_id="parent-1", child_id="child-1", uom="mm")

    assert removed["relationship_id"] == mm["relationship_id"]
    remaining = bom_service.get_bom_lines_by_parent_child("parent-1", "child-1")
    assert [line.id for line in remaining] == [ea["relationship_id"]]
    assert remaining[0].properties["uom"] == "EA"

