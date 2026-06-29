"""PLM-COLLAB Phase 7: governed BOM multi-table line WRITE-BACK route (ratified #901).

``PATCH /api/v1/bom/multitable/{part_id}/lines/{bom_line_id}`` applies a single BOM-line cell edit
IN PLACE (the Draft/editable-state fast path), guarded by a lifecycle lock, with a single
``meta_bom_writeback_audit`` row serving BOTH the single-use replay guard AND the before/after
audit. It is NOT a pending-ECO intent (the #896 draft is superseded); the ECO route is deferred.

A minimal FastAPI app mounts ONLY ``bom_multitable_router`` with ``get_db`` overridden to an
in-memory SQLite session and ``get_current_user`` overridden to drive the gate. Entitlement is
TEST-ONLY force-mapped to ``plm.collab`` so the REAL ``is_entitled`` query path runs.

Pins (the #901 §5/§7 acceptance, verified not assumed):
- unentitled WRITE -> 403 (first; before the key check, no existence-leak); unpermitted -> 403.
- missing Idempotency-Key -> 400; empty whitelist -> 400 (both before any object lookup).
- part missing -> 404; line not a "Part BOM" DIRECT child of part_id (source_id) -> 404.
- lifecycle-locked parent (real LifecycleState version_lock=True) -> 409; an unlocked parent -> 200.
- success -> 200 {ok, bom_line_id} (NO eco_id); the cell is applied IN PLACE; a before/after audit
  row is written.
- replay: same Idempotency-Key + same payload -> cached 200, NO re-apply, ONE audit row; same key +
  DIFFERENT payload -> 409.
- an audit/commit failure rolls the property mutation back (no partial state).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importing the app registers ALL ORM models on Base.metadata (Item/lifecycle/audit FK web).
from yuantus.api.app import create_app  # noqa: F401
from yuantus.api.dependencies.auth import get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.models.base import Base
from yuantus.meta_engine.app_framework import entitlement_service as es
from yuantus.meta_engine.app_framework.store_models import AppLicense
from yuantus.meta_engine.lifecycle.models import LifecycleMap, LifecycleState
from yuantus.meta_engine.models.bom_writeback_audit import BomWritebackAudit
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.meta_engine.web.bom_multitable_router import bom_multitable_router

WRITE_FEATURE = "bom_multitable_writeback"
APP = "plm.collab"
TENANT = "default"
ROUTE = "/api/v1/bom/multitable/{part_id}/lines/{bom_line_id}"
KEY = {"Idempotency-Key": "wb-0001"}


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _single_mode(monkeypatch):
    monkeypatch.setenv("YUANTUS_TENANCY_MODE", "single")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client(db_session, *, user="auth"):
    app = FastAPI()
    app.include_router(bom_multitable_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    if user == "auth":
        app.dependency_overrides[get_current_user] = lambda: _USER
    elif user == "unauth":
        def _unauth():
            raise HTTPException(status_code=401, detail="Unauthorized")

        app.dependency_overrides[get_current_user] = _unauth
    return TestClient(app, raise_server_exceptions=False)


_USER = type("_User", (), {"id": 7, "roles": ["engineer"], "is_superuser": False})()


def _entitle(monkeypatch, db_session):
    monkeypatch.setitem(es.FEATURE_APP_NAMES, WRITE_FEATURE, frozenset({APP}))
    db_session.add(
        AppLicense(id="licw", app_name=APP, license_key="keyw", status="Active", tenant_id=TENANT)
    )
    db_session.commit()


def _allow_permission(monkeypatch, *, allow=True):
    monkeypatch.setattr(MetaPermissionService, "check_permission", lambda self, *a, **k: allow)


def _part(item_id, *, state="In Work", item_type="Part"):
    return Item(
        id=item_id,
        item_type_id=item_type,
        config_id=item_id,
        generation=1,
        is_current=True,
        state=state,
        properties={"item_number": item_id, "name": item_id},
    )


def _bom_line(rel_id, *, parent, child, item_type="Part BOM", **cells):
    props = {"quantity": 2, "uom": "EA", "find_num": "10", "refdes": "R1"}
    props.update(cells)
    return Item(
        id=rel_id,
        item_type_id=item_type,
        config_id=rel_id,
        is_current=True,
        state="In Work",
        source_id=parent,
        related_id=child,
        properties=props,
    )


def _bom(db_session):
    """P1 -[R1]-> C1. No ItemType row -> is_item_locked is inert (unlocked) for the happy path."""
    db_session.add(_part("P1"))
    db_session.add(_part("C1", state="Released"))
    db_session.add(_bom_line("R1", parent="P1", child="C1"))
    db_session.commit()


# --- entitlement / permission (before the key + lookups) ---------------------

def test_unentitled_is_403(db_session):
    _bom(db_session)
    # no license + no key -> still 403 (entitlement is the FIRST gate, before the 400 key check).
    r = _client(db_session).patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5})
    assert r.status_code == 403


def test_unentitled_and_missing_part_is_403_not_404(db_session):
    # G1: entitlement is checked BEFORE the part lookup, so a missing part on a write surface
    # leaks no existence -- 403, never 404.
    r = _client(db_session).patch(
        ROUTE.format(part_id="GHOST", bom_line_id="R1"), json={"quantity": 5}, headers=KEY
    )
    assert r.status_code == 403


def test_unpermitted_is_403(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch, allow=False)
    _bom(db_session)
    r = _client(db_session).patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5})
    assert r.status_code == 403


# --- 400: missing key / empty patch (before any object lookup) ---------------

def test_missing_idempotency_key_is_400(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _bom(db_session)
    r = _client(db_session).patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5})
    assert r.status_code == 400


def test_empty_patch_is_400(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _bom(db_session)
    r = _client(db_session).patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={}, headers=KEY)
    assert r.status_code == 400



@pytest.mark.parametrize("bad", [True, [1, 2], {"x": 1}])
def test_non_scalar_quantity_is_rejected_422(db_session, monkeypatch, bad):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _bom(db_session)
    # quantity must be number|string|null -- a bool/list/object never reaches a governed BOM cell.
    r = _client(db_session).patch(
        ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": bad}, headers=KEY
    )
    assert r.status_code == 422

# --- 404: part / line-in-part ------------------------------------------------

def test_part_missing_is_404(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    r = _client(db_session).patch(ROUTE.format(part_id="NOPE", bom_line_id="R1"), json={"quantity": 5}, headers=KEY)
    assert r.status_code == 404


def test_line_not_direct_child_or_non_bom_is_404(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    db_session.add(_part("P1"))
    db_session.add(_part("P2"))
    # R1 is a real "Part BOM" but its source is P2, NOT P1 (the path part) -> line ∉ part -> 404
    db_session.add(_bom_line("R1", parent="P2", child="P1"))
    # X1 is a direct child of P1 but NOT a "Part BOM" -> 404
    db_session.add(_bom_line("X1", parent="P1", child="P2", item_type="Document Part"))
    db_session.commit()
    c = _client(db_session)
    assert c.patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5}, headers=KEY).status_code == 404
    assert c.patch(ROUTE.format(part_id="P1", bom_line_id="X1"), json={"quantity": 5}, headers=KEY).status_code == 404
    assert c.patch(ROUTE.format(part_id="P1", bom_line_id="GONE"), json={"quantity": 5}, headers=KEY).status_code == 404


# --- 409: real lifecycle lock (per #901 §5, the pact can't prove this) -------

def _locked_bom(db_session, *, version_lock):
    db_session.add(LifecycleMap(id="map1", name="Part Lifecycle"))
    db_session.add(
        LifecycleState(id="s1", name="Released", lifecycle_map_id="map1", version_lock=version_lock)
    )
    db_session.add(ItemType(id="Part", label="Part", lifecycle_map_id="map1"))
    db_session.add(ItemType(id="Part BOM", label="Part BOM"))
    db_session.add(_part("P1", state="Released"))
    db_session.add(_part("C1", state="Released"))
    db_session.add(_bom_line("R1", parent="P1", child="C1"))
    db_session.commit()


def test_lifecycle_locked_parent_is_409(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _locked_bom(db_session, version_lock=True)  # a REAL LifecycleState with version_lock
    r = _client(db_session).patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5}, headers=KEY)
    assert r.status_code == 409


def test_unlocked_parent_is_200(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _locked_bom(db_session, version_lock=False)  # same state name but NOT version-locking
    r = _client(db_session).patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5}, headers=KEY)
    assert r.status_code == 200


# --- success: in-place apply, audited, no eco_id -----------------------------

def test_success_applies_in_place_and_audits(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _bom(db_session)

    r = _client(db_session).patch(
        ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5, "refdes": "R9"}, headers=KEY
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True, "bom_line_id": "R1"}  # NO eco_id

    db_session.expire_all()
    # the cell is applied IN PLACE (not a pending intent)
    line = db_session.get(Item, "R1")
    assert line.properties["quantity"] == 5
    assert line.properties["refdes"] == "R9"
    assert line.properties["uom"] == "EA"  # untouched cell preserved

    # one audit+replay row, with the before/after diff
    audits = db_session.query(BomWritebackAudit).all()
    assert len(audits) == 1
    assert audits[0].idempotency_key == "wb-0001"
    assert audits[0].before["quantity"] == 2
    assert audits[0].after["quantity"] == 5 and audits[0].after["refdes"] == "R9"
    assert audits[0].part_id == "P1" and audits[0].bom_line_id == "R1"


# --- replay / single-use -----------------------------------------------------

def test_replay_same_key_same_payload_is_cached_200_no_double_apply(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _bom(db_session)
    c = _client(db_session)

    first = c.patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5}, headers=KEY)
    second = c.patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5}, headers=KEY)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"ok": True, "bom_line_id": "R1"}
    # a retried relay does NOT double-apply: still exactly one audit row
    assert db_session.query(BomWritebackAudit).count() == 1


def test_replay_same_key_different_payload_is_409(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _bom(db_session)
    c = _client(db_session)

    first = c.patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5}, headers=KEY)
    second = c.patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 9}, headers=KEY)
    assert first.status_code == 200
    assert second.status_code == 409
    db_session.expire_all()
    assert db_session.get(Item, "R1").properties["quantity"] == 5  # the 409 did not apply
    assert db_session.query(BomWritebackAudit).count() == 1



def test_replay_same_key_different_line_is_409(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    db_session.add(_part("P1"))
    db_session.add(_part("C1", state="Released"))
    db_session.add(_part("C2", state="Released"))
    db_session.add(_bom_line("R1", parent="P1", child="C1"))
    db_session.add(_bom_line("R2", parent="P1", child="C2"))
    db_session.commit()
    c = _client(db_session)

    first = c.patch(ROUTE.format(part_id="P1", bom_line_id="R1"), json={"quantity": 5}, headers=KEY)
    # SAME key, DIFFERENT line (even with identical cells) -> 409, never the first line's result.
    second = c.patch(ROUTE.format(part_id="P1", bom_line_id="R2"), json={"quantity": 5}, headers=KEY)
    assert first.status_code == 200
    assert second.status_code == 409

