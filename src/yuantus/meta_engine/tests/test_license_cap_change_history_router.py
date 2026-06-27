"""Admin seat-cap change-history route (L4 Fork B): GET /api/v1/admin/license-cap-history.

Mounts only license_cap_change_history_router on a minimal FastAPI app with get_db
overridden to in-memory SQLite and require_superuser overridden (mirrors
test_license_status_router). Inserts AuditLog rows in the shape
record_seat_cap_audit writes and asserts parsing/auth/filter/cache.
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
from yuantus.database import get_db
from yuantus.meta_engine.web.license_cap_change_history_router import (
    license_cap_change_history_router,
)
from yuantus.models.audit import AuditLog
from yuantus.models.base import Base

TENANT = "tenant-1"
URL = "/api/v1/admin/license-cap-history"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[AuditLog.__table__])
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _client(db_session, *, superuser=True):
    app = FastAPI()
    app.include_router(license_cap_change_history_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session
    if superuser:
        app.dependency_overrides[require_superuser] = lambda: object()
    else:
        def _deny():
            raise HTTPException(status_code=403, detail="superuser required")

        app.dependency_overrides[require_superuser] = _deny
    return TestClient(app)


def _cap_audit(db_session, *, tenant=TENANT, max_users):
    # mirrors record_seat_cap_audit: path=f"cli:license/seat-cap?max_users={cap}"
    db_session.add(
        AuditLog(
            id=uuid.uuid4().hex,
            method="LICENSE",
            path=f"cli:license/seat-cap?max_users={max_users}",
            tenant_id=tenant,
            status_code=200,
            duration_ms=0,
        )
    )
    db_session.commit()


def _other_license_audit(db_session, *, tenant=TENANT):
    # a LICENSE audit that is NOT a seat-cap change (e.g. import) — must be excluded
    db_session.add(
        AuditLog(
            id=uuid.uuid4().hex,
            method="LICENSE",
            path="cli:license/import",
            tenant_id=tenant,
            status_code=200,
            duration_ms=0,
        )
    )
    db_session.commit()


def test_unknown_tenant_is_empty_200_not_404(db_session):
    r = _client(db_session).get(URL, params={"tenant_id": "nobody"})
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "nobody"
    assert body["changes"] == [] and body["count"] == 0


def test_set_caps_are_parsed(db_session):
    _cap_audit(db_session, max_users=10)
    _cap_audit(db_session, max_users=20)
    body = _client(db_session).get(URL, params={"tenant_id": TENANT}).json()
    assert body["count"] == 2
    caps = {c["max_users"] for c in body["changes"]}
    assert caps == {10, 20}
    assert all(c["cleared"] is False for c in body["changes"])


def test_cleared_cap_is_none_and_flagged(db_session):
    _cap_audit(db_session, max_users="cleared")
    body = _client(db_session).get(URL, params={"tenant_id": TENANT}).json()
    assert body["count"] == 1
    assert body["changes"][0]["max_users"] is None
    assert body["changes"][0]["cleared"] is True


def test_excludes_non_seat_cap_license_audits(db_session):
    _cap_audit(db_session, max_users=5)
    _other_license_audit(db_session)  # import audit — must NOT appear
    body = _client(db_session).get(URL, params={"tenant_id": TENANT}).json()
    assert body["count"] == 1 and body["changes"][0]["max_users"] == 5


def test_tenant_isolation(db_session):
    _cap_audit(db_session, tenant=TENANT, max_users=7)
    _cap_audit(db_session, tenant="other", max_users=99)
    body = _client(db_session).get(URL, params={"tenant_id": TENANT}).json()
    assert body["count"] == 1 and body["changes"][0]["max_users"] == 7


def test_blank_tenant_id_is_400(db_session):
    assert _client(db_session).get(URL, params={"tenant_id": "   "}).status_code == 400


def test_requires_superuser(db_session):
    assert _client(db_session, superuser=False).get(URL, params={"tenant_id": TENANT}).status_code == 403


def test_sets_cache_control_no_store(db_session):
    r = _client(db_session).get(URL, params={"tenant_id": TENANT})
    assert r.headers.get("Cache-Control") == "no-store"


def test_router_exposes_exactly_one_route():
    assert len(license_cap_change_history_router.routes) == 1
