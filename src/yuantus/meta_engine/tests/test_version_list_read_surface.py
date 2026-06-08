"""CAD-PDM Superseded read-surface: ``VersionService.list_versions`` + the
``GET /api/v1/versions/items/{item_id}/versions`` route.

Makes B1 (#735) version-axis semantics VISIBLE in the read layer. Spec:
``docs/DEVELOPMENT_ODOOPLM_19_CADPDM_SUPERSEDE_READ_SURFACE_TASKBOOK_20260607.md``.

- D3 ``lifecycle_status``: ONE derived value per version, FIRST-MATCH order
  (``historical_released`` -> ``active_released`` -> ``in_work`` -> ``draft``).
  ``is_superseded`` stays a raw FLAG -- never a peer status (a version is never both
  ``historical_released`` AND ``superseded``). The order is written so a stale
  ``state == "Superseded"`` / ``is_current`` cannot skew the classification.
- D3 ``in_work`` is DERIVED from ``is_under_modification`` (item-level): an open draft
  with NO released ancestor is ``draft``, NOT ``in_work``.
- D6 sort: stable ``generation ASC, created_at ASC, id ASC`` (revision is a string +
  branch/merge makes it unstable); missing item -> 404 (``VersionError``), never a
  faked empty list.
- D5 auth: the route inherits the router's OPTIONAL dep, so the happy path needs no
  auth wiring -- a read surface no narrower than the sibling mutations.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.version.service import VersionError, VersionService
from yuantus.meta_engine.web.version_lifecycle_router import version_lifecycle_router
from yuantus.models import user as _user  # noqa: F401 - registers users table
from yuantus.models.base import Base

import_all_models()


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'supersede-read.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    yield db
    db.close()


def _item(session, iid: str) -> Item:
    it = Item(
        id=iid,
        item_type_id="Part",
        config_id=f"c-{iid}-{uuid.uuid4()}",
        generation=1,
        is_current=True,
    )
    session.add(it)
    session.flush()
    return it


def _version(
    session,
    item: Item,
    *,
    gen: int = 1,
    rev: str = "A",
    released: bool,
    current: bool,
    predecessor_id: str | None = None,
    branch: str = "main",
    superseded: bool = False,
    state: str | None = None,
    created_at: datetime | None = None,
    vid: str | None = None,
) -> ItemVersion:
    v = ItemVersion(
        id=vid or f"v-{uuid.uuid4()}",
        item_id=item.id,
        generation=gen,
        revision=rev,
        version_label=f"{gen}.{rev}",
        state=state or ("Released" if released else "Draft"),
        is_current=current,
        is_released=released,
        is_superseded=superseded,
        predecessor_id=predecessor_id,
        branch_name=branch,
    )
    if created_at is not None:
        v.created_at = created_at
    session.add(v)
    session.flush()
    if current:
        item.current_version_id = v.id
        session.flush()
    return v


def _lineage(session, iid: str = "P"):
    """P with three lifecycle states on one line (only v3 is open-current -> the
    partial-unique is satisfied): v1 historical_released, v2 active_released,
    v3 in_work (open draft + released ancestors -> is_under_modification True).
    v1 carries the realistic ``state="Superseded"`` to prove the classifier reads the
    FLAGS, not the state string."""
    item = _item(session, iid)
    v1 = _version(
        session, item, gen=1, rev="A", released=True, current=False,
        superseded=True, state="Superseded",
    )
    v2 = _version(
        session, item, gen=1, rev="B", released=True, current=False,
        predecessor_id=v1.id,
    )
    v3 = _version(
        session, item, gen=1, rev="C", released=False, current=True,
        predecessor_id=v2.id,
    )
    session.commit()
    return item, v1, v2, v3


def _by_id(payload) -> dict:
    return {row["version_id"]: row for row in payload["versions"]}


# ---------- D6: missing item -> 404 (not an empty list) -----------------------
def test_list_versions_missing_item_raises_not_found(session):
    with pytest.raises(VersionError, match="not found"):
        VersionService(session).list_versions("does-not-exist")


# ---------- D3: the four-state taxonomy ---------------------------------------
def test_lifecycle_status_four_state_taxonomy(session):
    item, v1, v2, v3 = _lineage(session, "P")
    # A separate item Q: a lone never-released open draft -> draft (NOT in_work,
    # because no released ancestor -> is_under_modification False).
    q = _item(session, "Q")
    vq = _version(session, q, gen=1, rev="A", released=False, current=True)
    session.commit()

    rows_p = _by_id(VersionService(session).list_versions("P"))
    assert rows_p[v1.id]["lifecycle_status"] == "historical_released"
    assert rows_p[v2.id]["lifecycle_status"] == "active_released"
    assert rows_p[v3.id]["lifecycle_status"] == "in_work"

    rows_q = _by_id(VersionService(session).list_versions("Q"))
    assert rows_q[vq.id]["lifecycle_status"] == "draft"


# ---------- D3: in_work is DERIVED from is_under_modification ------------------
def test_in_work_is_derived_from_under_modification(session):
    # Same SHAPE on both items (open current unreleased draft), opposite classification:
    # only the item with a released ancestor is "under modification" -> in_work.
    item_p, _v1, _v2, v3 = _lineage(session, "P")
    q = _item(session, "Q")
    vq = _version(session, q, gen=1, rev="A", released=False, current=True)
    session.commit()

    svc = VersionService(session)
    payload_p = svc.list_versions("P")
    payload_q = svc.list_versions("Q")

    assert payload_p["is_under_modification"] is True
    assert payload_q["is_under_modification"] is False
    # The open drafts are byte-for-byte the same shape (unreleased + current); ONLY the
    # derived predicate flips the status.
    assert _by_id(payload_p)[v3.id]["is_current"] is True
    assert _by_id(payload_p)[v3.id]["is_released"] is False
    assert _by_id(payload_p)[v3.id]["lifecycle_status"] == "in_work"
    assert _by_id(payload_q)[vq.id]["is_current"] is True
    assert _by_id(payload_q)[vq.id]["is_released"] is False
    assert _by_id(payload_q)[vq.id]["lifecycle_status"] == "draft"


# ---------- D2/D3: is_superseded stays a readable FLAG (not folded away) -------
def test_is_superseded_flag_preserved_alongside_status(session):
    _item_p, v1, v2, _v3 = _lineage(session, "P")
    rows = _by_id(VersionService(session).list_versions("P"))
    # The superseded version: flag readable AND a single derived status (not both at once).
    assert rows[v1.id]["is_superseded"] is True
    assert rows[v1.id]["lifecycle_status"] == "historical_released"
    assert rows[v1.id]["state"] == "Superseded"  # raw state visible, but does not skew status
    # The active released version: flag is False, status active_released.
    assert rows[v2.id]["is_superseded"] is False
    assert rows[v2.id]["lifecycle_status"] == "active_released"


# ---------- D6: stable sort generation ASC, created_at ASC, id ASC -------------
def test_versions_sorted_generation_then_created_at_then_id(session):
    # Released non-current versions (so the partial-unique on open drafts is moot),
    # seeded in SCRAMBLED order with hand-set created_at + ids so each sort key is the
    # decider for a distinct pair:
    #   - gen1 C(Jan1) before B(Jan2): created_at beats revision ("Z" < "A" is False)
    #     AND beats id ("v-c" > "v-b") -> created_at is the real key, not those.
    #   - gen2 A after all gen1: generation is primary.
    #   - gen3 F,G share created_at -> id ASC ("v-f1" < "v-f2") is the tie-breaker.
    item = _item(session, "P")
    common = dict(released=True, current=False)
    a = _version(session, item, gen=2, rev="A", vid="v-a",
                 created_at=datetime(2026, 1, 3), **common)
    g = _version(session, item, gen=3, rev="A2", vid="v-f2",
                 created_at=datetime(2026, 1, 4), **common)
    c = _version(session, item, gen=1, rev="Z", vid="v-c",
                 created_at=datetime(2026, 1, 1), **common)
    f = _version(session, item, gen=3, rev="A", vid="v-f1",
                 created_at=datetime(2026, 1, 4), **common)
    b = _version(session, item, gen=1, rev="A", vid="v-b",
                 created_at=datetime(2026, 1, 2), **common)
    session.commit()

    ordered = [row["version_id"] for row in VersionService(session).list_versions("P")["versions"]]
    assert ordered == [c.id, b.id, a.id, f.id, g.id]


# ---------- D1/D5: the route serializes the payload + 404 ----------------------
def _client(session) -> TestClient:
    app = FastAPI()
    app.include_router(version_lifecycle_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: session
    # The route inherits the router's auth dep (D5: a read no narrower than the
    # mutations). In the test env auth mode is "required", so the dep 401s without a
    # token -- override it to a fixed authenticated caller, the same way the other
    # version-router tests stub auth. (The endpoint declares the alias
    # ``get_current_user_id``, which IS ``get_current_user_id_optional``, so this
    # override matches by object identity.)
    app.dependency_overrides[get_current_user_id_optional] = lambda: 1
    return TestClient(app)


def test_router_serializes_versions_and_404(session):
    _item_p, v1, _v2, _v3 = _lineage(session, "P")
    client = _client(session)

    resp = client.get("/api/v1/versions/items/P/versions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["item_id"] == "P"
    assert body["is_under_modification"] is True
    assert len(body["versions"]) == 3
    row = _by_id(body)[v1.id]
    # the derived field + the raw flags both serialize over the wire
    assert row["lifecycle_status"] == "historical_released"
    assert row["is_superseded"] is True
    assert {"version_id", "lifecycle_status", "is_released", "is_current",
            "generation", "revision", "predecessor_id", "created_at"} <= set(row)

    missing = client.get("/api/v1/versions/items/NOPE/versions")
    assert missing.status_code == 404
