"""PLM-COLLAB Phase-7: governed BOM multi-table WRITE-back route (design-lock #901 + G1-G5).

Mirrors the read-route test harness (in-memory SQLite, REAL is_entitled, monkeypatched
permission). Pins the G1-G5 build-conformance gates as runnable provider tests:

- G1 guard order: write-entitlement 403 -> permission 403 -> 400 -> 404 -> 409. Crucially an
  unentitled caller (or one with a missing part / bad header / bad body) gets **403, never
  404/400/422** -- the write surface leaks no existence and FastAPI pre-validation cannot run
  ahead of the gate (the route reads the header/body manually with Request).
- 400 boundaries: missing / blank / >64 Idempotency-Key; malformed body; unknown-only body
  (empty whitelist).
- G5: the 409 lifecycle lock is proven with a REAL LifecycleState(version_lock=True); a Draft
  parent -> 200 (the pact fixture is inert on lifecycle, so this MUST be a provider test).
- G3 replay: same key + same payload -> cached 200 with NO second write (DB-reload assert);
  same key + DIFFERENT payload -> 409. Audit row captures before/after; an audit/mutation
  failure rolls back atomically.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importing the app registers ALL ORM models on Base.metadata (Item's FK web).
from yuantus.api.app import create_app  # noqa: F401
from yuantus.api.dependencies.auth import get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.models.base import Base
from yuantus.meta_engine.app_framework import entitlement_service as es
from yuantus.meta_engine.app_framework.store_models import AppLicense
from yuantus.meta_engine.lifecycle.models import LifecycleState
from yuantus.meta_engine.models.bom_writeback_audit import BomWritebackAudit
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.meta_permission_service import MetaPermissionService
from yuantus.meta_engine.web.bom_multitable_router import bom_multitable_router

WRITE_FEATURE = "bom_multitable_writeback"
APP = "plm.collab"
TENANT = "default"
PATCH_PATH = "/api/v1/bom/multitable/{part_id}/lines/{bom_line_id}"
_USER = type("_User", (), {"id": 7, "roles": ["engineer"], "is_superuser": False})()
_HDR = {"Idempotency-Key": "idem-key-0001"}


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
    else:
        def _unauth():
            raise HTTPException(status_code=401, detail="Unauthorized")

        app.dependency_overrides[get_current_user] = _unauth
    return TestClient(app)


def _entitle(monkeypatch, db_session):
    """TEST-ONLY force-entitle the WRITE key via plm.collab, exercising REAL is_entitled."""
    monkeypatch.setitem(es.FEATURE_APP_NAMES, WRITE_FEATURE, frozenset({APP}))
    db_session.add(
        AppLicense(id="licW", app_name=APP, license_key="keyW", status="Active", tenant_id=TENANT)
    )
    db_session.commit()


def _allow_permission(monkeypatch, *, allow=True):
    monkeypatch.setattr(
        MetaPermissionService, "check_permission", lambda self, *a, **k: allow
    )


def _seed(db_session, *, part_state="Draft", current_state=None):
    db_session.add(
        Item(
            id="P1", item_type_id="Part", config_id="P1", generation=1, is_current=True,
            state=part_state, current_state=current_state,
        )
    )
    db_session.add(
        Item(id="C1", item_type_id="Part", config_id="C1", generation=1, is_current=True, state="Draft")
    )
    db_session.add(
        Item(
            id="R1", item_type_id="Part BOM", config_id="R1", is_current=True,
            source_id="P1", related_id="C1",
            properties={"quantity": 4, "uom": "ea", "find_num": "10", "refdes": "B1"},
        )
    )
    db_session.commit()


def _url(part="P1", line="R1"):
    return PATCH_PATH.format(part_id=part, bom_line_id=line)


# --- G1: unentitled -> 403, NEVER 404/400/422 (no existence leak, no early FastAPI 422) -----

def test_unentitled_is_403_even_for_missing_part_and_bad_body(db_session, monkeypatch):
    _seed(db_session)

    def _explode(self, *a, **k):
        raise AssertionError("permission must not be checked when unentitled")

    monkeypatch.setattr(MetaPermissionService, "check_permission", _explode)
    c = _client(db_session)
    assert c.patch(_url(), json={"quantity": 9}, headers=_HDR).status_code == 403
    assert c.patch(_url(part="P999"), json={"quantity": 9}, headers=_HDR).status_code == 403
    # no Idempotency-Key AND malformed body -> still 403 (entitlement is the first gate).
    assert c.patch(_url(), content=b"{bad json", headers={}).status_code == 403


def test_permission_denied_is_403(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch, allow=False)
    _seed(db_session)
    assert _client(db_session).patch(_url(), json={"quantity": 9}, headers=_HDR).status_code == 403


# --- 400 boundaries -------------------------------------------------------------------------

@pytest.mark.parametrize(
    "headers", [{}, {"Idempotency-Key": "   "}, {"Idempotency-Key": "x" * 65}]
)
def test_missing_blank_or_oversize_idempotency_key_is_400(db_session, monkeypatch, headers):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    assert _client(db_session).patch(_url(), json={"quantity": 9}, headers=headers).status_code == 400


def test_malformed_body_is_400(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    assert _client(db_session).patch(_url(), content=b"{not json", headers=_HDR).status_code == 400


def test_unknown_only_body_empty_whitelist_is_400(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    r = _client(db_session).patch(_url(), json={"not_a_field": 1, "id": "x"}, headers=_HDR)
    assert r.status_code == 400


# --- 404: line not in part ------------------------------------------------------------------

def test_line_not_in_part_is_404(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    db_session.add(
        Item(id="P2", item_type_id="Part", config_id="P2", generation=1, is_current=True, state="Draft")
    )
    db_session.commit()
    c = _client(db_session)
    assert c.patch(_url(part="P2", line="R1"), json={"quantity": 9}, headers=_HDR).status_code == 404
    assert c.patch(_url(line="NOPE"), json={"quantity": 9}, headers=_HDR).status_code == 404


# --- G5: real lifecycle 409 + Draft 200 (+ DB-reload that the mutation persisted) -----------

def test_locked_parent_is_409(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    db_session.add(LifecycleState(id="st-locked", name="Released", version_lock=True))
    db_session.commit()
    _seed(db_session, part_state="Released", current_state="st-locked")
    assert _client(db_session).patch(_url(), json={"quantity": 9}, headers=_HDR).status_code == 409


def test_draft_parent_applies_200_and_persists(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    r = _client(db_session).patch(_url(), json={"quantity": 9, "refdes": "B7"}, headers=_HDR)
    assert r.status_code == 200 and r.json()["ok"] is True and r.json()["bom_line_id"] == "R1"
    # DB-reload: the mutation actually landed (copy-on-write reassign, not a phantom).
    db_session.expire_all()
    line = db_session.get(Item, "R1")
    assert line.properties["quantity"] == 9
    assert line.properties["refdes"] == "B7"
    assert line.properties["uom"] == "ea"  # untouched cell preserved


# --- G3: replay (no double write) + same-key-different-payload 409 + audit -------------------

def test_replay_same_key_same_payload_does_not_reapply(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    c = _client(db_session)
    assert c.patch(_url(), json={"quantity": 9}, headers=_HDR).status_code == 200
    # Tamper the cell out-of-band; a true replay must NOT re-apply the original write over it.
    db_session.expire_all()
    tampered = {**db_session.get(Item, "R1").properties, "quantity": 99}
    db_session.get(Item, "R1").properties = tampered
    db_session.commit()
    again = c.patch(_url(), json={"quantity": 9}, headers=_HDR)
    assert again.status_code == 200 and again.json().get("replayed") is True
    db_session.expire_all()
    assert db_session.get(Item, "R1").properties["quantity"] == 99  # NOT re-applied to 9
    assert db_session.query(BomWritebackAudit).count() == 1  # one row, not two


def test_same_key_different_payload_is_409(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    c = _client(db_session)
    assert c.patch(_url(), json={"quantity": 9}, headers=_HDR).status_code == 200
    assert c.patch(_url(), json={"quantity": 10}, headers=_HDR).status_code == 409


def test_audit_row_captures_before_and_after(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)
    assert _client(db_session).patch(_url(), json={"quantity": 9}, headers=_HDR).status_code == 200
    row = db_session.query(BomWritebackAudit).one()
    assert row.idempotency_key == _HDR["Idempotency-Key"]
    assert row.part_id == "P1" and row.bom_line_id == "R1"
    assert row.before == {"quantity": 4}
    assert row.after == {"quantity": 9}
    assert isinstance(row.request_hash, str) and len(row.request_hash) == 64


def test_mutation_failure_rolls_back_audit_atomically(db_session, monkeypatch):
    _entitle(monkeypatch, db_session)
    _allow_permission(monkeypatch)
    _seed(db_session)

    # autoflush OFF so flush() fires ONLY explicitly: #1 = audit insert (begin_nested),
    # #2 = the mutation flush. Fail exactly #2 to prove audit + mutation are atomic.
    db_session.autoflush = False
    real_flush = db_session.flush
    state = {"calls": 0}

    def flaky_flush(*a, **k):
        state["calls"] += 1
        if state["calls"] == 2:
            raise RuntimeError("boom-mutation-flush")
        return real_flush(*a, **k)

    monkeypatch.setattr(db_session, "flush", flaky_flush)

    app = FastAPI()
    app.include_router(bom_multitable_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: _USER
    client = TestClient(app, raise_server_exceptions=False)

    r = client.patch(_url(), json={"quantity": 9}, headers=_HDR)
    assert r.status_code == 500
    db_session.rollback()
    db_session.expire_all()
    # atomic: neither the audit row nor the mutation survived.
    assert db_session.query(BomWritebackAudit).count() == 0
    assert db_session.get(Item, "R1").properties["quantity"] == 4
