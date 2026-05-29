"""Service-logic tests for SpareService against real in-memory SQLite (G5).

DB-backed (NOT allowlisted): runs under regression, or locally with
``YUANTUS_PYTEST_DB=1``. Validates the logic the mocked router test cannot reach:
``ensure_spare_item_type`` idempotency, directional add/list/remove + dedup +
self-reference guards, and ``explode_spares`` over a REAL BOMService traversal
(multi-level + diamond dedup).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.spare_service import SPARE_ITEM_TYPE, SpareService
from yuantus.models.base import Base
from yuantus.models import user as _user  # noqa: F401 - registers users table

import_all_models()


def _part(session, item_id: str) -> Item:
    item = Item(
        id=item_id,
        item_type_id="Part",
        config_id=f"cfg-{item_id}",
        generation=1,
        is_current=True,
        state="Active",
        properties={"item_number": item_id},
    )
    session.add(item)
    return item


def _bom_edge(session, parent_id: str, child_id: str) -> Item:
    edge = Item(
        id=f"bom-{parent_id}-{child_id}",
        item_type_id="Part BOM",
        config_id=str(uuid.uuid4()),
        generation=1,
        is_current=True,
        state="Active",
        source_id=parent_id,
        related_id=child_id,
        properties={"quantity": 1},
    )
    session.add(edge)
    return edge


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'spare.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    s = SessionLocal()
    s.add_all(
        [
            ItemType(
                id="Part", label="Part", is_relationship=False, is_versionable=True
            ),
            ItemType(
                id="Part BOM",
                label="Part BOM",
                is_relationship=True,
                source_item_type_id="Part",
                related_item_type_id="Part",
            ),
        ]
    )
    s.commit()
    yield s
    s.close()


# --------------------------------------------------------------------------
# ensure_spare_item_type
# --------------------------------------------------------------------------


def test_ensure_spare_item_type_creates_and_is_idempotent(session):
    svc = SpareService(session)
    assert session.get(ItemType, SPARE_ITEM_TYPE) is None
    svc.ensure_spare_item_type()
    created = session.get(ItemType, SPARE_ITEM_TYPE)
    assert created is not None
    assert created.is_relationship is True
    # Second call must not raise or duplicate.
    svc.ensure_spare_item_type()
    rows = session.query(ItemType).filter_by(id=SPARE_ITEM_TYPE).all()
    assert len(rows) == 1


# --------------------------------------------------------------------------
# add_spare / list_spares / remove_spare
# --------------------------------------------------------------------------


def test_add_spare_creates_directional_relationship(session):
    _part(session, "ASSY")
    _part(session, "SPARE-A")
    session.commit()

    svc = SpareService(session)
    rel = svc.add_spare("ASSY", "SPARE-A", properties={"quantity": 3})
    assert rel.item_type_id == SPARE_ITEM_TYPE
    assert rel.source_id == "ASSY"
    assert rel.related_id == "SPARE-A"
    assert rel.properties == {"quantity": 3}


def test_add_spare_rejects_self_reference(session):
    _part(session, "ASSY")
    session.commit()
    svc = SpareService(session)
    with pytest.raises(ValueError, match="cannot be a spare of itself"):
        svc.add_spare("ASSY", "ASSY")


def test_add_spare_rejects_non_part(session):
    _part(session, "ASSY")
    session.commit()
    svc = SpareService(session)
    with pytest.raises(ValueError, match="Invalid Part ID"):
        svc.add_spare("ASSY", "MISSING")


def test_add_spare_rejects_duplicate(session):
    _part(session, "ASSY")
    _part(session, "SPARE-A")
    session.commit()
    svc = SpareService(session)
    svc.add_spare("ASSY", "SPARE-A")
    with pytest.raises(ValueError, match="already exists"):
        svc.add_spare("ASSY", "SPARE-A")


def test_list_spares_is_directional(session):
    _part(session, "ASSY")
    _part(session, "SPARE-A")
    _part(session, "OTHER")
    session.commit()
    svc = SpareService(session)
    svc.add_spare("ASSY", "SPARE-A")

    listed = svc.list_spares("ASSY")
    assert [e["spare_item_id"] for e in listed] == ["SPARE-A"]
    # The spare part itself has no spares designated under it (directional).
    assert svc.list_spares("SPARE-A") == []
    assert svc.list_spares("OTHER") == []


def test_remove_spare_deletes_relationship(session):
    _part(session, "ASSY")
    _part(session, "SPARE-A")
    session.commit()
    svc = SpareService(session)
    rel = svc.add_spare("ASSY", "SPARE-A")
    svc.remove_spare(rel.id, user_id=1)
    assert svc.list_spares("ASSY") == []
    with pytest.raises(ValueError, match="not found"):
        svc.remove_spare(rel.id, user_id=1)


# --------------------------------------------------------------------------
# explode_spares (real BOMService traversal)
# --------------------------------------------------------------------------


def test_explode_collects_spares_down_assembly(session):
    # ASSY -> CHILD (Part BOM). Spares on both levels.
    _part(session, "ASSY")
    _part(session, "CHILD")
    _part(session, "SPARE-A")
    _part(session, "SPARE-B")
    _part(session, "SPARE-C")
    _bom_edge(session, "ASSY", "CHILD")
    session.commit()

    svc = SpareService(session)
    svc.add_spare("ASSY", "SPARE-A")
    svc.add_spare("ASSY", "SPARE-B")
    svc.add_spare("CHILD", "SPARE-C")

    groups = svc.explode_spares("ASSY")
    by_item = {g["item_id"]: g for g in groups}
    assert set(by_item) == {"ASSY", "CHILD"}
    assert by_item["ASSY"]["count"] == 2
    assert by_item["CHILD"]["count"] == 1
    # Document order: root first.
    assert groups[0]["item_id"] == "ASSY"


def test_explode_dedupes_diamond_shared_part(session):
    # ASSY -> B, ASSY -> C, B -> SHARED, C -> SHARED (diamond on SHARED).
    for pid in ("ASSY", "B", "C", "SHARED", "SPARE-X"):
        _part(session, pid)
    _bom_edge(session, "ASSY", "B")
    _bom_edge(session, "ASSY", "C")
    _bom_edge(session, "B", "SHARED")
    _bom_edge(session, "C", "SHARED")
    session.commit()

    svc = SpareService(session)
    svc.add_spare("SHARED", "SPARE-X")

    groups = svc.explode_spares("ASSY")
    shared_groups = [g for g in groups if g["item_id"] == "SHARED"]
    # SHARED is reachable via two paths but must appear exactly once.
    assert len(shared_groups) == 1
    assert shared_groups[0]["count"] == 1
