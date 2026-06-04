"""PLM-COLLAB-P1-D: feature-entitlement affordance routes.

A minimal FastAPI app mounts only ``feature_router`` with ``get_db`` overridden to
an in-memory SQLite session and ``require_superuser`` overridden, so the routes are
exercised without the full app lifespan. Tenancy is left at the single-mode
"default" tenant (no reliance on ContextVar propagation into the request worker).

Pins:
- GET status: unentitled -> upgrade.available True; entitled -> upgrade.available
  False; unknown feature_key -> 400
- POST mock-activate: 404 when the flag is off (default); superuser-only; only
  plm_collaboration_pro; activating flips is_entitled to True; idempotent
- the router exposes exactly the 2 affordance routes
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from yuantus.api.dependencies.admin_auth import require_superuser
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.models.base import Base
from yuantus.meta_engine.app_framework.models import AppRegistry
from yuantus.meta_engine.app_framework.store_models import AppLicense
from yuantus.meta_engine.web.feature_router import feature_router
from yuantus.security.rbac.models import RBACUser

FEATURE = "plm_collaboration_pro"
TENANT = "default"  # single-mode resolved tenant when no request context is set


@pytest.fixture
def db_session():
    # StaticPool + check_same_thread=False: FastAPI runs sync handlers in a
    # threadpool, so the in-memory SQLite session must be usable across threads.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[RBACUser.__table__, AppRegistry.__table__, AppLicense.__table__],
    )
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _single_mode(monkeypatch):
    monkeypatch.setenv("YUANTUS_TENANCY_MODE", "single")
    monkeypatch.delenv("YUANTUS_FEATURE_MOCK_ACTIVATION_ENABLED", raising=False)
    monkeypatch.delenv("YUANTUS_TEST_FAILPOINTS_ENABLED", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client(db_session, *, superuser=True):
    app = FastAPI()
    app.include_router(feature_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    if superuser:
        app.dependency_overrides[require_superuser] = lambda: object()
    else:
        def _deny():
            raise HTTPException(status_code=403, detail="superuser required")

        app.dependency_overrides[require_superuser] = _deny
    return TestClient(app)


def _add_license(db_session, *, app_name="plm.collab"):
    db_session.add(
        AppLicense(
            id=uuid.uuid4().hex,
            app_name=app_name,
            license_key=uuid.uuid4().hex,
            status="Active",
            tenant_id=TENANT,
        )
    )
    db_session.commit()


def test_status_unentitled_offers_upgrade(db_session):
    body = _client(db_session).get(f"/api/v1/features/{FEATURE}").json()
    assert body["entitled"] is False
    assert body["upgrade"]["available"] is True


def test_status_entitled_no_upgrade(db_session):
    _add_license(db_session)
    body = _client(db_session).get(f"/api/v1/features/{FEATURE}").json()
    assert body["entitled"] is True
    assert body["upgrade"]["available"] is False


def test_status_unknown_feature_key_returns_400(db_session):
    r = _client(db_session).get("/api/v1/features/not_a_feature")
    assert r.status_code == 400


def test_mock_activate_default_off_is_404(db_session):
    r = _client(db_session).post(f"/api/v1/features/{FEATURE}/mock-activate")
    assert r.status_code == 404


def test_mock_activate_flag_off_404s_before_superuser_check(db_session):
    # default-off must 404 BEFORE require_superuser runs, so the path looks absent
    # even to a caller that would fail the superuser check -- so DON'T override
    # require_superuser here (the flag gate must short-circuit first).
    app = FastAPI()
    app.include_router(feature_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    r = TestClient(app).post(f"/api/v1/features/{FEATURE}/mock-activate")
    assert r.status_code == 404


def test_mock_activate_requires_superuser(db_session, monkeypatch):
    monkeypatch.setenv("YUANTUS_FEATURE_MOCK_ACTIVATION_ENABLED", "true")
    get_settings.cache_clear()
    r = _client(db_session, superuser=False).post(f"/api/v1/features/{FEATURE}/mock-activate")
    assert r.status_code == 403


def test_mock_activate_only_supports_collab_feature(db_session, monkeypatch):
    monkeypatch.setenv("YUANTUS_FEATURE_MOCK_ACTIVATION_ENABLED", "true")
    get_settings.cache_clear()
    r = _client(db_session).post("/api/v1/features/bom_multitable/mock-activate")
    assert r.status_code == 400


def test_mock_activate_enabled_flips_entitlement(db_session, monkeypatch):
    monkeypatch.setenv("YUANTUS_FEATURE_MOCK_ACTIVATION_ENABLED", "true")
    get_settings.cache_clear()
    client = _client(db_session)
    assert client.get(f"/api/v1/features/{FEATURE}").json()["entitled"] is False
    r = client.post(f"/api/v1/features/{FEATURE}/mock-activate")
    assert r.status_code == 200
    assert r.json()["entitled"] is True and r.json()["mock"] is True
    assert client.get(f"/api/v1/features/{FEATURE}").json()["entitled"] is True


def test_mock_activate_is_idempotent(db_session, monkeypatch):
    monkeypatch.setenv("YUANTUS_FEATURE_MOCK_ACTIVATION_ENABLED", "true")
    get_settings.cache_clear()
    client = _client(db_session)
    client.post(f"/api/v1/features/{FEATURE}/mock-activate")
    client.post(f"/api/v1/features/{FEATURE}/mock-activate")
    n = db_session.query(AppLicense).filter(AppLicense.license_key.like("mock:%")).count()
    assert n == 1


def test_router_exposes_exactly_two_routes():
    assert len(feature_router.routes) == 2
