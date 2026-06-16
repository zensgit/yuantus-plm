"""WP3.4 C2 (opt-in): SearchService ``released_only`` -> latest-released face.

``released_only=True`` restricts results to *current* items whose current
``ItemVersion`` is released (``is_released`` lives on the version, not the ``Item``,
matching ``LatestReleasedGuardService``). Default ``False`` preserves browsing
drafts/WIP. The filter is on the search surface only -- never the general
``GetOperation``. Exercises the DB fallback path (``client`` forced to ``None``).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.search_service import SearchService
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.models import user as _user  # noqa: F401 - registers users table
from yuantus.models.base import Base

import_all_models()


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'search-released.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    db.add(ItemType(id="Part", label="Part", is_versionable=True))
    db.commit()
    yield db
    db.close()


def _versioned_item(session, item_id: str, *, released: bool) -> Item:
    ver = ItemVersion(
        id=f"v-{item_id}-{uuid.uuid4()}",
        item_id=item_id,
        generation=1,
        revision="A",
        version_label="1.A",
        state="Released" if released else "Draft",
        is_current=True,
        is_released=released,
    )
    session.add(ver)
    session.flush()
    item = Item(
        id=item_id,
        item_type_id="Part",
        config_id=f"c-{item_id}-{uuid.uuid4()}",
        generation=1,
        is_current=True,
        current_version_id=ver.id,
        state="Released" if released else "Draft",
        properties={"item_number": item_id, "name": f"name-{item_id}"},
    )
    session.add(item)
    session.flush()
    return item


def _unversioned_item(session, item_id: str) -> Item:
    item = Item(
        id=item_id,
        item_type_id="Part",
        config_id=f"c-{item_id}-{uuid.uuid4()}",
        generation=1,
        is_current=True,
        current_version_id=None,
        state="Draft",
        properties={"item_number": item_id, "name": f"name-{item_id}"},
    )
    session.add(item)
    session.flush()
    return item


def _svc(session) -> SearchService:
    svc = SearchService(session)
    svc.client = None  # force the DB fallback path deterministically
    return svc


def test_released_only_filters_to_latest_released_face(session):
    _versioned_item(session, "A", released=True)
    _versioned_item(session, "B", released=False)  # current but version not released
    _unversioned_item(session, "C")  # current but no version at all
    session.commit()

    svc = _svc(session)

    default_hits = {h["id"] for h in svc.search("", released_only=False)["hits"]}
    assert default_hits == {"A", "B", "C"}  # browsing shows drafts/WIP

    released_hits = svc.search("", released_only=True)
    assert {h["id"] for h in released_hits["hits"]} == {"A"}  # only the released face
    assert released_hits["total"] == 1


def test_released_only_default_is_off(session):
    # Default call (no released_only) must be unchanged -- non-breaking.
    _versioned_item(session, "B", released=False)
    session.commit()
    hits = _svc(session).search("")["hits"]
    assert {h["id"] for h in hits} == {"B"}


def test_build_doc_carries_latest_released_signal(session):
    a = _versioned_item(session, "A", released=True)
    b = _versioned_item(session, "B", released=False)
    c = _unversioned_item(session, "C")
    session.commit()
    svc = _svc(session)
    assert svc._build_doc(a)["is_released"] is True
    assert svc._build_doc(a)["is_current"] is True
    assert svc._build_doc(b)["is_released"] is False  # current, version not released
    assert svc._build_doc(c)["is_released"] is False  # current, no version
