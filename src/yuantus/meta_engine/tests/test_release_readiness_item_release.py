"""B2 readiness aggregation: item_release diagnostics surface in release_readiness.

The assembly-release hard gate (`bom.children_all_released`) is shown *advisorily*
here -- a blocking or missing child appears in the readiness resource set BEFORE
promote, not only as a last-second hard stop. D1: the `item_release` resource
appears ONLY when the item has >=1 direct ASSEMBLY edge (child present OR dangling);
a leaf part has nothing to show. These are SERVICE-level tests that exercise the
real aggregation (the router contract test mocks the service, so it cannot).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.lifecycle.models import (
    LifecycleMap,
    LifecycleState,
    LifecycleTransition,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.service import RelationshipService
from yuantus.meta_engine.services.release_readiness_service import (
    ReleaseReadinessService,
)
from yuantus.models import user as _user  # noqa: F401 - registers users table
from yuantus.models.base import Base

import_all_models()


@pytest.fixture(autouse=True)
def _hermetic_settings_cache():
    """`release_validation` reads the lru-cached `get_settings()`; a prior test
    that sets a bad `RELEASE_VALIDATION_RULESETS_JSON` and fails before its own
    `cache_clear()` would leak it. Start/end clean (see test_item_release_gate)."""
    from yuantus.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'readiness-item-release.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    _seed_lifecycle(db)
    yield db
    db.close()


def _seed_lifecycle(session) -> None:
    session.add(LifecycleMap(id="map1", name="Part Lifecycle"))
    session.add(
        LifecycleState(id="state_draft", name="Draft", lifecycle_map_id="map1", is_start_state=True)
    )
    session.add(
        LifecycleState(id="state_released", name="Released", lifecycle_map_id="map1", is_released=True)
    )
    session.add(
        LifecycleTransition(
            id="t1",
            lifecycle_map_id="map1",
            from_state_id="state_draft",
            to_state_id="state_released",
        )
    )
    session.add(ItemType(id="Part", label="Part", is_versionable=False, lifecycle_map_id="map1"))
    session.add(
        ItemType(
            id="ASSEMBLY",
            label="Assembly",
            is_relationship=True,
            is_versionable=False,
            source_item_type_id="Part",
            related_item_type_id="Part",
        )
    )
    session.commit()


def _item(session, iid: str, *, released: bool = False) -> Item:
    it = Item(
        id=iid,
        item_type_id="Part",
        config_id=f"c-{iid}-{uuid.uuid4()}",
        generation=1,
        is_current=True,
        is_versionable=False,
        state="Released" if released else "Draft",
        current_state="state_released" if released else "state_draft",
        properties={"item_number": iid},
    )
    session.add(it)
    return it


def _assembly(session, parent: str, child: str) -> None:
    RelationshipService(session).create_relationship(parent, child, "ASSEMBLY")
    session.commit()


def _dangling_assembly_edge(session, parent: str, ghost: str = "GHOST") -> str:
    edge_id = f"edge-{parent}-{ghost}"
    session.add(
        Item(
            id=edge_id,
            item_type_id="ASSEMBLY",
            config_id=f"edge-{uuid.uuid4()}",
            generation=1,
            is_current=True,
            source_id=parent,
            related_id=ghost,
        )
    )
    session.commit()
    return edge_id


def _readiness(session, item_id: str, *, ruleset_id: str = "readiness") -> dict:
    return ReleaseReadinessService(session).get_item_release_readiness(
        item_id=item_id,
        ruleset_id=ruleset_id,
        mbom_limit=20,
        routing_limit=20,
        baseline_limit=20,
    )


def _item_release_resources(payload) -> list:
    return [r for r in payload["resources"] if r["kind"] == "item_release"]


# D3 case 1 + D4 -- unreleased direct child surfaces as an item_release error.
def test_readiness_surfaces_unreleased_child(session):
    _item(session, "P")
    _item(session, "C")  # Draft -> unreleased
    session.commit()
    _assembly(session, "P", "C")

    payload = _readiness(session, "P")
    res = _item_release_resources(payload)
    assert len(res) == 1
    assert res[0]["resource_type"] == "item"
    assert res[0]["resource_id"] == "P"
    assert res[0]["name"] == "P"  # D4: item_number from properties
    assert res[0]["state"] == "Draft"  # D4: item.state
    assert res[0]["errors"][0].rule_id == "bom.children_all_released"
    # D3 case 3: summary/by_kind include the new resource.
    by_kind = payload["summary"]["by_kind"]["item_release"]
    assert by_kind["resources"] == 1
    assert by_kind["error_count"] == 1
    assert payload["summary"]["ok"] is False


# D3 case 2 -- a dangling ASSEMBLY edge surfaces as child_missing (fail-closed).
def test_readiness_surfaces_dangling_edge(session):
    _item(session, "P")
    session.commit()
    _dangling_assembly_edge(session, "P")

    res = _item_release_resources(_readiness(session, "P"))
    assert len(res) == 1
    assert res[0]["errors"][0].code == "child_missing"


# D1 semantic -- assembly with ALL children released: resource present, 0 errors
# (this is the case has_assembly_edges exists for; errors alone could not include it).
def test_readiness_all_released_shows_ok_resource(session):
    _item(session, "P")
    _item(session, "C", released=True)
    session.commit()
    _assembly(session, "P", "C")

    payload = _readiness(session, "P")
    res = _item_release_resources(payload)
    assert len(res) == 1
    assert res[0]["errors"] == []
    assert payload["summary"]["by_kind"]["item_release"]["ok_resources"] == 1


# D3 case 4 -- a leaf part (no ASSEMBLY edges) produces NO item_release resource.
def test_readiness_leaf_has_no_item_release_resource(session):
    _item(session, "P")
    session.commit()

    payload = _readiness(session, "P")
    assert _item_release_resources(payload) == []
    assert "item_release" not in payload["summary"]["by_kind"]
