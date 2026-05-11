#!/usr/bin/env python3
"""SQLite DB end-to-end verification for CAD material sync.

This is the strongest macOS-side validation before a Windows + AutoCAD smoke:
it uses the local CAD fixture, the Yuantus cad-material-sync router, and a real
in-memory SQLAlchemy database with the PLM Item/ItemType tables.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import verify_material_sync_e2e as plugin_e2e
import verify_material_sync_fixture as fixture_tools


ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "material_sync_mock_drawing.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def material_sync_db_tables(yuantus_root: Path) -> tuple[Any, list[Any]]:
    src = yuantus_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from yuantus.models.base import Base
    from yuantus.meta_engine.lifecycle.models import (
        LifecycleMap,
        LifecycleState,
        LifecycleTransition,
        StateIdentityPermission,
    )
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType, Property
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

    tables = [
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
        ItemVersion.__table__,
        Item.__table__,
    ]
    return Base, tables


def build_db(yuantus_root: Path):
    Base, tables = material_sync_db_tables(yuantus_root)
    from yuantus.meta_engine.models.meta_schema import ItemType

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=tables)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    db.add(
        ItemType(
            id="Part",
            label="Part",
            is_relationship=False,
            is_versionable=False,
            version_control_enabled=False,
        )
    )
    db.commit()
    return db, Base, tables


def build_client(plugin_module: Any, db: Any) -> TestClient:
    app = FastAPI()
    app.include_router(plugin_module.router, prefix="/api/v1")
    app.dependency_overrides[plugin_module._get_db] = lambda: db
    app.dependency_overrides[plugin_module._current_user] = lambda: SimpleNamespace(
        id="1",
        roles=["admin"],
        is_superuser=True,
    )
    return TestClient(app)


def main() -> int:
    yuantus_root = plugin_e2e.find_yuantus_root()
    plugin_module = plugin_e2e.load_yuantus_plugin(yuantus_root)
    db, Base, tables = build_db(yuantus_root)

    try:
        client = build_client(plugin_module, db)
        fixture = json.loads(fixture_tools.read(FIXTURE))
        aliases = fixture_tools.load_aliases()
        extracted = fixture_tools.extract_fields(fixture, aliases)

        dry_run = client.post(
            "/api/v1/plugins/cad-material-sync/sync/inbound",
            json={
                "profile_id": "sheet",
                "cad_fields": extracted,
                "create_if_missing": True,
                "dry_run": True,
            },
        )
        require(dry_run.status_code == 200, f"dry-run failed: {dry_run.text}")
        dry_run_payload = dry_run.json()
        require(dry_run_payload["ok"] is True, f"dry-run not ok: {dry_run_payload}")
        require(dry_run_payload["action"] == "created", f"unexpected dry-run action: {dry_run_payload}")
        require(dry_run_payload["properties"]["specification"] == "1200*600*12", f"unexpected dry-run spec: {dry_run_payload}")

        from yuantus.meta_engine.models.item import Item

        require(db.query(Item).count() == 0, "dry-run must not create a DB Item")

        create = client.post(
            "/api/v1/plugins/cad-material-sync/sync/inbound",
            json={
                "profile_id": "sheet",
                "cad_fields": dry_run_payload["cad_fields"],
                "create_if_missing": True,
                "dry_run": False,
            },
        )
        require(create.status_code == 200, f"create failed: {create.text}")
        create_payload = create.json()
        item_id = create_payload.get("item_id")
        require(create_payload["ok"] is True and item_id, f"create not ok: {create_payload}")
        item = db.get(Item, item_id)
        require(item is not None, f"created item not found: {item_id}")
        require(item.properties["material"] == "Q235B", f"unexpected created material: {item.properties}")
        require(item.properties["specification"] == "1200*600*12", f"unexpected created spec: {item.properties}")

        update = client.post(
            "/api/v1/plugins/cad-material-sync/sync/inbound",
            json={
                "profile_id": "sheet",
                "item_id": item_id,
                "cad_fields": {
                    **dry_run_payload["cad_fields"],
                    "材料": "Q355B",
                },
                "overwrite": True,
                "dry_run": False,
            },
        )
        require(update.status_code == 200, f"update failed: {update.text}")
        update_payload = update.json()
        require(update_payload["ok"] is True, f"update not ok: {update_payload}")
        require(update_payload["action"] == "updated", f"unexpected update action: {update_payload}")
        db.refresh(item)
        require(item.properties["material"] == "Q355B", f"material not updated: {item.properties}")

        outbound = client.post(
            "/api/v1/plugins/cad-material-sync/sync/outbound",
            json={
                "profile_id": "sheet",
                "item_id": item_id,
                "include_empty": False,
            },
        )
        require(outbound.status_code == 200, f"outbound failed: {outbound.text}")
        outbound_payload = outbound.json()
        require(outbound_payload["cad_fields"]["材料"] == "Q355B", f"unexpected outbound material: {outbound_payload}")
        require(outbound_payload["cad_fields"]["规格"] == "1200*600*12", f"unexpected outbound spec: {outbound_payload}")

        applied = deepcopy(fixture)
        applied["apply_fields"] = outbound_payload["cad_fields"]
        updated_cells = fixture_tools.apply_fields(applied, aliases)
        require(updated_cells >= 2, f"expected material/spec fixture updates, got {updated_cells}")
        require(applied["blocks"][0]["attributes"]["材料"] == "Q355B", f"block material not applied: {applied}")
        require(applied["tables"][0][0][3] == "Q355B", f"table material not applied: {applied}")
        require(applied["tables"][0][2][0] == "规格=1200*600*12", f"table spec not applied: {applied}")

        print("OK: material sync SQLite DB create/update/outbound e2e passed")
        return 0
    finally:
        db.close()
        Base.metadata.drop_all(bind=db.get_bind(), tables=list(reversed(tables)))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
