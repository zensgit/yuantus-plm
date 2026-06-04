"""Phase 2 — assistant resolve/create endpoint tests (read-only resolve, create re-read + Draft)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from yuantus.models.base import Base
from yuantus.meta_engine.lifecycle.models import (
    LifecycleMap,
    LifecycleState,
    LifecycleTransition,
    StateIdentityPermission,
)
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType, Property
from yuantus.meta_engine.models.plugin_config import PluginConfig
from yuantus.meta_engine.permission.models import Access, Permission
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.workflow.models import WorkflowMap
from yuantus.security.rbac.models import (
    RBACPermission,
    RBACResource,
    RBACRole,
    RBACUser,
    rbac_user_permissions,
    rbac_user_roles,
    role_permissions,
)

RESOLVE = "/api/v1/plugins/cad-material-sync/assistant/resolve"
CREATE = "/api/v1/plugins/cad-material-sync/assistant/create"


def _load_plugin_module():
    # Distinct module name from test_plugin_cad_material_sync so the two do not
    # collide in sys.modules during the combined plugin-tests CI run.
    root = Path(__file__).resolve().parents[4]
    plugin_path = root / "plugins" / "yuantus-cad-material-sync" / "main.py"
    spec = importlib.util.spec_from_file_location("cad_material_assistant_plugin", plugin_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tables():
    return [
        RBACResource.__table__,
        RBACPermission.__table__,
        RBACRole.__table__,
        RBACUser.__table__,
        rbac_user_roles,
        role_permissions,
        rbac_user_permissions,
        Permission.__table__,
        Access.__table__,
        WorkflowMap.__table__,
        LifecycleMap.__table__,
        LifecycleState.__table__,
        LifecycleTransition.__table__,
        StateIdentityPermission.__table__,
        ItemType.__table__,
        Property.__table__,
        PluginConfig.__table__,
        ItemVersion.__table__,
        Item.__table__,
    ]


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_tables())
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    db.add(ItemType(id="Part", label="Part", is_relationship=False, is_versionable=False,
                    version_control_enabled=False))
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=list(reversed(_tables())))


def _client(module, db):
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1")
    app.dependency_overrides[module._get_db] = lambda: db
    app.dependency_overrides[module._current_user] = lambda: SimpleNamespace(
        id="1", roles=["admin"], is_superuser=True
    )
    return TestClient(app)


def _add_part(db, item_id, properties, *, state="Released"):
    db.add(Item(id=item_id, item_type_id="Part", config_id=str(uuid4()), generation=1,
                state=state, properties=properties))
    db.commit()


def _attach_part_lifecycle(db):
    """给 Part ItemType 挂一个起始态为 Draft 的 lifecycle（覆盖 §5.3 对齐分支）。"""
    db.add(LifecycleMap(id="lc_part", name="Part Lifecycle"))
    db.add(LifecycleState(id="st_draft", lifecycle_map_id="lc_part", name="Draft",
                          is_start_state=True, is_suspended=False))
    part = db.get(ItemType, "Part")
    part.lifecycle_map_id = "lc_part"
    db.add(part)
    db.commit()


def _committed_item_count(db):
    """Count via a fresh session on the same engine — committed delta, not in-session pending."""
    fresh = sessionmaker(bind=db.get_bind(), expire_on_commit=False)()
    try:
        return fresh.query(Item).count()
    finally:
        fresh.close()


# --------------------------------------------------------------------------- #
# resolve (read-only)
# --------------------------------------------------------------------------- #
def test_resolve_is_read_only(session):
    module = _load_plugin_module()
    client = _client(module, session)
    before = _committed_item_count(session)
    resp = client.post(RESOLVE, json={
        "profile_id": "bar",
        "values": {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100},
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # 约束 1：零写入（committed delta == 0）
    assert _committed_item_count(session) == before


def test_resolve_returns_exact_match_and_no_draft(session):
    module = _load_plugin_module()
    client = _client(module, session)
    _add_part(session, "exact", {"material_category": "bar", "material": "Q235",
                                 "specification": "Φ20*100"})
    resp = client.post(RESOLVE, json={
        "profile_id": "bar",
        "values": {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100},
    }).json()
    assert any(m["id"] == "exact" for m in resp["exact_matches"])
    assert resp["draft_suggested"] is False


def test_resolve_suggests_draft_when_no_match(session):
    module = _load_plugin_module()
    client = _client(module, session)
    resp = client.post(RESOLVE, json={
        "profile_id": "bar",
        "values": {"material_category": "bar", "material": "X-UNIQUE-9", "diameter": 7, "length": 3},
    }).json()
    assert resp["exact_matches"] == []
    assert resp["draft_suggested"] is True


def test_resolve_lists_similar_but_not_high_for_different_size(session):
    module = _load_plugin_module()
    client = _client(module, session)
    _add_part(session, "sim", {"material_category": "bar", "material": "Q235",
                               "diameter": 25, "length": 100, "specification": "Φ25*100"})
    resp = client.post(RESOLVE, json={
        "profile_id": "bar",
        "values": {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100},
    }).json()
    sims = {c["id"]: c for c in resp["similar_candidates"]}
    assert "sim" in sims
    assert sims["sim"]["high_similar"] is False


def test_resolve_infers_profile_when_id_missing(session):
    module = _load_plugin_module()
    client = _client(module, session)
    resp = client.post(RESOLVE, json={
        "values": {"material_category": "bar", "material": "Q235", "diameter": 20, "length": 100},
    })
    assert resp.status_code == 200
    assert resp.json()["profile_id"] == "bar"


# --------------------------------------------------------------------------- #
# create (re-read + Draft)
# --------------------------------------------------------------------------- #
def test_create_returns_reread_fields_no_lifecycle_warns(session):
    module = _load_plugin_module()
    client = _client(module, session)
    resp = client.post(CREATE, json={
        "profile_id": "bar",
        "properties": {"material_category": "bar", "material": "Q235", "diameter": 20,
                       "length": 100, "item_number": "BAR-001"},
    }).json()
    assert resp["ok"] is True
    assert resp["item_id"]
    assert resp["item_number"] == "BAR-001"
    # default fixture has no lifecycle for Part -> warning branch, not Draft
    assert resp["draft_check"]["is_draft"] is False
    assert resp["draft_check"].get("warning") == "no_lifecycle_start_state"
    # item actually persisted
    assert session.get(Item, resp["item_id"]) is not None


def test_create_aligns_state_to_lifecycle_start(session):
    module = _load_plugin_module()
    _attach_part_lifecycle(session)
    client = _client(module, session)
    resp = client.post(CREATE, json={
        "profile_id": "bar",
        "properties": {"material_category": "bar", "material": "Q235", "diameter": 20,
                       "length": 100, "item_number": "BAR-002"},
    }).json()
    assert resp["ok"] is True
    # §5.3 aligned branch: state == start.name, current_state == start.id
    assert resp["state"] == "Draft"
    assert resp["current_state"] == "st_draft"
    assert resp["draft_check"]["is_start_state"] is True
    assert resp["draft_check"]["is_draft"] is True


def test_create_rejects_invalid_without_writing(session):
    module = _load_plugin_module()
    client = _client(module, session)
    before = _committed_item_count(session)
    resp = client.post(CREATE, json={
        "profile_id": "bar",
        "properties": {"material_category": "bar", "material": "Q235", "diameter": "not-a-number",
                       "length": 100},
    }).json()
    assert resp["ok"] is False
    assert resp["errors"]
    assert _committed_item_count(session) == before
