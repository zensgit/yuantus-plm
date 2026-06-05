"""B2: assembly release hard gate contracts.

A released parent must not reference unreleased direct ASSEMBLY children (WP1.2
CAD product structure). Enforced as a HARD block at LifecycleService.promote and
exposed via ItemReleaseService.get_release_diagnostics.
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
from yuantus.meta_engine.lifecycle.service import LifecycleService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.service import RelationshipService
from yuantus.meta_engine.services.item_release_service import ItemReleaseService
from yuantus.models import user as _user  # noqa: F401 - registers users table
from yuantus.models.base import Base

import_all_models()


@pytest.fixture(autouse=True)
def _hermetic_settings_cache():
    """Order-independence. ``release_validation`` reads the lru_cached
    ``get_settings()``; a prior test that sets a bad
    ``YUANTUS_RELEASE_VALIDATION_RULESETS_JSON`` and fails before its own
    ``cache_clear()`` (e.g. on a local 401) would leak that bad config into the
    cache and break ``get_release_ruleset`` here. Start and end each test clean."""
    from yuantus.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'item-release.db'}",
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
    """A current ASSEMBLY edge whose related_id points at a non-existent child.
    create_relationship() rejects a missing related item, so build the edge Item
    directly (same shape: source_id / item_type_id / is_current). Returns edge id."""
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


def _rule_ids(diag) -> set:
    return {e.rule_id for e in diag["errors"]}


# ---------- ItemReleaseService evaluator -------------------------------------
def test_diag_unreleased_child_errors(session):
    _item(session, "P")
    _item(session, "C")  # Draft -> unreleased
    session.commit()
    _assembly(session, "P", "C")

    diag = ItemReleaseService(session).get_release_diagnostics("P", ruleset_id="readiness")
    assert "bom.children_all_released" in _rule_ids(diag)
    assert diag["errors"][0].details["child_id"] == "C"


def test_diag_released_child_ok(session):
    _item(session, "P")
    _item(session, "C", released=True)
    session.commit()
    _assembly(session, "P", "C")

    diag = ItemReleaseService(session).get_release_diagnostics("P", ruleset_id="readiness")
    assert diag["errors"] == []


def test_diag_no_children_is_vacuous_pass(session):
    _item(session, "P")
    session.commit()
    assert ItemReleaseService(session).get_release_diagnostics("P", ruleset_id="readiness")["errors"] == []


def test_diag_default_flags_already_released(session):
    _item(session, "P", released=True)
    session.commit()
    diag = ItemReleaseService(session).get_release_diagnostics("P", ruleset_id="default")
    assert "item.not_already_released" in _rule_ids(diag)


def test_diag_readiness_skips_not_already_released(session):
    _item(session, "P", released=True)
    session.commit()
    diag = ItemReleaseService(session).get_release_diagnostics("P", ruleset_id="readiness")
    assert "item.not_already_released" not in _rule_ids(diag)


def test_diag_missing_item(session):
    diag = ItemReleaseService(session).get_release_diagnostics("nope")
    assert "item.exists" in _rule_ids(diag)


def test_diag_dangling_edge_blocks(session):
    # ASSEMBLY edge exists but related_id points at a missing item -> fail CLOSED.
    _item(session, "P")
    session.commit()
    edge_id = _dangling_assembly_edge(session, "P")

    diag = ItemReleaseService(session).get_release_diagnostics("P", ruleset_id="readiness")
    missing = [e for e in diag["errors"] if e.code == "child_missing"]
    assert missing, "dangling ASSEMBLY edge must produce a child_missing error"
    assert missing[0].rule_id == "bom.children_all_released"
    assert missing[0].details["relationship_id"] == edge_id


def test_diag_approved_string_without_state_row_blocks(session):
    # No resolvable LifecycleState row, state="Approved": NOT released (Approved is
    # an approval/ECO concept, not a Part release state) -> must block.
    _item(session, "P")
    session.add(
        Item(
            id="C",
            item_type_id="Part",
            config_id=f"c-C-{uuid.uuid4()}",
            generation=1,
            is_current=True,
            is_versionable=False,
            state="Approved",
            current_state=None,
            properties={"item_number": "C"},
        )
    )
    session.commit()
    _assembly(session, "P", "C")

    diag = ItemReleaseService(session).get_release_diagnostics("P", ruleset_id="readiness")
    assert "child_not_released" in {e.code for e in diag["errors"]}


# ---------- promote hard gate (real LifecycleService.promote) ----------------
def test_promote_blocks_on_unreleased_child(session):
    _item(session, "P")
    _item(session, "C")  # Draft
    session.commit()
    _assembly(session, "P", "C")

    p = session.get(Item, "P")
    res = LifecycleService(session).promote(p, "Released", user_id=1)
    assert res.success is False
    assert "not released" in (res.error or "")
    assert p.state == "Draft"  # never mutated -- not released


def test_promote_blocks_on_dangling_edge(session):
    # A broken BOM reference (dangling ASSEMBLY edge) must hard-block release.
    _item(session, "P")
    session.commit()
    _dangling_assembly_edge(session, "P")

    p = session.get(Item, "P")
    res = LifecycleService(session).promote(p, "Released", user_id=1)
    assert res.success is False
    assert "missing" in (res.error or "").lower()
    assert p.state == "Draft"  # never mutated


def test_promote_succeeds_when_children_released(session):
    _item(session, "P")
    _item(session, "C", released=True)
    session.commit()
    _assembly(session, "P", "C")

    p = session.get(Item, "P")
    res = LifecycleService(session).promote(p, "Released", user_id=1)
    assert res.success is True
    assert p.state == "Released"


def test_promote_leaf_succeeds(session):
    _item(session, "P")
    session.commit()
    p = session.get(Item, "P")
    res = LifecycleService(session).promote(p, "Released", user_id=1)
    assert res.success is True
    assert p.state == "Released"
