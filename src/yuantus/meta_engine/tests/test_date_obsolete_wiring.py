"""CAD-PDM C3 Slice 2 — worker gating + drain, and admin ops routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.context import tenant_id_var
from yuantus.database import get_db
from yuantus.meta_engine.app_framework.store_models import AppLicense
from yuantus.meta_engine.models.date_obsolete import DateObsoleteImpact
from yuantus.meta_engine.models.effectivity import Effectivity
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services import date_obsolete_worker as worker_mod
from yuantus.meta_engine.services.date_obsolete_worker import DateObsoleteWorker
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.models.base import Base

_NOW = datetime(2026, 6, 18, 12, 0, 0)
_PAST = _NOW - timedelta(days=2)
_ADMIN = SimpleNamespace(id=1, roles=["admin"], is_superuser=True)
_C3_APP = "plm.cadpdm_date_obsolete"   # the SKU registered for cadpdm_date_obsolete
_TENANT = "t-c3"


@pytest.fixture()
def tenant_ctx():
    tok = tenant_id_var.set(_TENANT)
    try:
        yield _TENANT
    finally:
        tenant_id_var.reset(tok)


def _license(db, *, tenant_id=_TENANT, app_name=_C3_APP, status="Active"):
    db.add(AppLicense(id=str(uuid.uuid4()), app_name=app_name,
                      license_key=str(uuid.uuid4()).upper(), status=status,
                      tenant_id=tenant_id, license_data={}))
    db.commit()


@pytest.fixture(autouse=True)
def _auth_optional(monkeypatch):
    monkeypatch.setattr(
        "yuantus.api.middleware.auth_enforce.get_settings",
        lambda: SimpleNamespace(AUTH_MODE="optional"),
    )
    yield


@pytest.fixture()
def Session():
    from yuantus.meta_engine.bootstrap import import_all_models
    from yuantus.models import user as _user  # noqa: F401

    import_all_models()
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng, expire_on_commit=False)


@pytest.fixture()
def db(Session):
    s = Session()
    try:
        yield s
    finally:
        s.close()


def _settings(enabled=True):
    return SimpleNamespace(
        DATE_EFFECTIVITY_OBSOLETE_ENABLED=enabled,
        DATE_EFFECTIVITY_OBSOLETE_BATCH_SIZE=100,
        DATE_EFFECTIVITY_OBSOLETE_POLL_INTERVAL_SECONDS=300,
        DATE_EFFECTIVITY_OBSOLETE_SYSTEM_USER_ID=0,
    )


def _seed_expired(db):
    db.add(Item(id="C", config_id="C", item_type_id="t", state="Released", is_current=True, properties={}))
    db.add(Item(id="P", config_id="P", item_type_id="t", source_id=None, related_id=None, is_current=True, properties={}))
    db.add(Item(id="R", config_id="R", item_type_id="bom", source_id="P", related_id="C", is_current=True, properties={}))
    db.add(ItemVersion(id="vC", item_id="C", state="Released", is_current=True, is_released=True))
    db.add(Effectivity(id="e1", version_id="vC", effectivity_type="Date",
                       start_date=_PAST - timedelta(days=10), end_date=_PAST))
    db.commit()


# -- worker gating + drain ---------------------------------------------------
def test_worker_disabled_is_noop(db, monkeypatch):
    monkeypatch.setattr(worker_mod, "get_settings", lambda: _settings(enabled=False))
    _seed_expired(db)
    n = DateObsoleteWorker().run_once_with_session(db)
    assert n == 0
    assert db.query(DateObsoleteImpact).count() == 0


def test_worker_enabled_but_not_entitled_is_noop(db, monkeypatch, tenant_ctx):
    # REAL entitlement path: enabled globally, but NO active license for this tenant
    # -> is_entitled returns False -> no-op (no monkeypatch of is_entitled).
    monkeypatch.setattr(worker_mod, "get_settings", lambda: _settings(enabled=True))
    _seed_expired(db)
    assert DateObsoleteWorker().run_once_with_session(db) == 0
    assert db.query(DateObsoleteImpact).count() == 0


def test_worker_enabled_and_entitled_drains(db, monkeypatch, tenant_ctx):
    # REAL entitlement path: enabled + an Active AppLicense for plm.cadpdm_date_obsolete
    # under this tenant -> is_entitled returns True -> drains. Proves the gate CAN flip
    # true (the registered key is reachable), not just a monkeypatched stub.
    monkeypatch.setattr(worker_mod, "get_settings", lambda: _settings(enabled=True))
    _license(db)
    _seed_expired(db)
    n = DateObsoleteWorker().run_once_with_session(db)
    assert n == 1
    flag = db.query(DateObsoleteImpact).one()
    assert flag.parent_item_id == "P" and flag.child_item_id == "C"


def test_worker_drains_all_beyond_batch_size(db, monkeypatch, tenant_ctx):
    # batch_size must NOT bound TOTAL reachable work: 2 expired effectivities on distinct
    # parents + batch_size=1 -> ONE tick still flags BOTH (process-all + idempotent).
    monkeypatch.setattr(worker_mod, "get_settings", lambda: _settings(enabled=True))
    _license(db)
    for i in (1, 2):
        db.add(Item(id=f"C{i}", config_id=f"C{i}", item_type_id="t", state="Released", is_current=True, properties={}))
        db.add(Item(id=f"P{i}", config_id=f"P{i}", item_type_id="t", is_current=True, properties={}))
        db.add(Item(id=f"R{i}", config_id=f"R{i}", item_type_id="bom", source_id=f"P{i}", related_id=f"C{i}", is_current=True, properties={}))
        db.add(ItemVersion(id=f"vC{i}", item_id=f"C{i}", state="Released", is_current=True, is_released=True))
        db.add(Effectivity(id=f"e{i}", version_id=f"vC{i}", effectivity_type="Date",
                           start_date=_PAST - timedelta(days=10), end_date=_PAST))
    db.commit()
    DateObsoleteWorker(batch_size=1).run_once_with_session(db)
    db.commit()
    flagged = {f.parent_item_id for f in db.query(DateObsoleteImpact).all()}
    assert flagged == {"P1", "P2"}   # both reached despite batch_size=1


def test_worker_run_once_short_circuits_when_disabled(monkeypatch):
    # global kill-switch off => run_once returns 0 without opening a session.
    monkeypatch.setattr(worker_mod, "get_settings", lambda: _settings(enabled=False))
    called = {"n": 0}
    monkeypatch.setattr(worker_mod, "get_db_session", lambda: called.__setitem__("n", 1))
    assert DateObsoleteWorker().run_once() == 0
    assert called["n"] == 0


# -- ops routes --------------------------------------------------------------
@pytest.fixture()
def client(Session):
    app = create_app()
    def _override_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()
    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: _ADMIN
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _impact(db, iid, state="open"):
    db.add(DateObsoleteImpact(id=iid, effectivity_id=f"e-{iid}", child_item_id="C", parent_item_id="P",
                              child_obsoleted=False, reason="child_effectivity_expired", state=state,
                              detected_at=_NOW))
    db.commit()


def test_ops_list_and_filter(client, db):
    _impact(db, "i1", "open"); _impact(db, "i2", "acknowledged")
    assert client.get("/api/v1/cadpdm/date-obsolete-impacts").json()["count"] == 2
    r = client.get("/api/v1/cadpdm/date-obsolete-impacts?state=open")
    assert r.json()["count"] == 1 and r.json()["rows"][0]["state"] == "open"


def test_ops_invalid_state_422(client, db):
    assert client.get("/api/v1/cadpdm/date-obsolete-impacts?state=bogus").status_code == 422


def test_ops_get_404(client, db):
    assert client.get("/api/v1/cadpdm/date-obsolete-impacts/ghost").status_code == 404


def test_ops_acknowledge(client, db):
    _impact(db, "i9", "open")
    r = client.post("/api/v1/cadpdm/date-obsolete-impacts/i9/acknowledge")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "acknowledged" and body["acknowledged_by_id"] == 1
    assert body["acknowledged_at"] is not None


def test_ops_acknowledge_404(client, db):
    assert client.post("/api/v1/cadpdm/date-obsolete-impacts/ghost/acknowledge").status_code == 404
