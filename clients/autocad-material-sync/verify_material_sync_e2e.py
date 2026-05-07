#!/usr/bin/env python3
"""macOS end-to-end verification for CAD material sync.

This script bridges the local AutoCAD client fixture with the Yuantus
cad-material-sync FastAPI router:

1. Extract fields from a mock drawing fixture.
2. Send them to /sync/inbound as a dry-run create/update.
3. Apply returned cad_fields back to the mock drawing.
4. Verify /sync/outbound returns the same CAD package from PLM properties.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

import verify_material_sync_fixture as fixture_tools


ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "material_sync_mock_drawing.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def find_yuantus_root() -> Path:
    env_root = os.environ.get("YUANTUS_ROOT")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        require((root / "plugins" / "yuantus-cad-material-sync" / "main.py").exists(), f"invalid YUANTUS_ROOT: {root}")
        return root

    candidates = [
        ROOT.parents[1],
        ROOT.parents[1].parent / "Yuantus",
        ROOT.parents[2] / "Yuantus",
    ]
    for root in candidates:
        if (root / "plugins" / "yuantus-cad-material-sync" / "main.py").exists():
            return root.resolve()
    raise AssertionError("Yuantus root not found; set YUANTUS_ROOT=/path/to/Yuantus")


def load_yuantus_plugin(yuantus_root: Path):
    src = yuantus_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    plugin_path = yuantus_root / "plugins" / "yuantus-cad-material-sync" / "main.py"
    spec = importlib.util.spec_from_file_location("cad_material_sync_plugin_e2e", plugin_path)
    require(spec is not None and spec.loader is not None, f"cannot load plugin: {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_client(plugin_module: Any) -> TestClient:
    app = FastAPI()
    app.include_router(plugin_module.router, prefix="/api/v1")
    app.dependency_overrides[plugin_module._get_db] = lambda: None
    app.dependency_overrides[plugin_module._current_user] = lambda: SimpleNamespace(id="fixture-user")
    return TestClient(app)


def main() -> int:
    yuantus_root = find_yuantus_root()
    plugin_module = load_yuantus_plugin(yuantus_root)
    client = build_client(plugin_module)

    fixture = json.loads(fixture_tools.read(FIXTURE))
    aliases = fixture_tools.load_aliases()
    extracted = fixture_tools.extract_fields(fixture, aliases)
    require(extracted == fixture["expected_extract"], f"unexpected fixture extract: {extracted}")

    inbound = client.post(
        "/api/v1/plugins/cad-material-sync/sync/inbound",
        json={
            "profile_id": "sheet",
            "cad_fields": extracted,
            "dry_run": True,
            "create_if_missing": True,
            "overwrite": False,
        },
    )
    require(inbound.status_code == 200, f"inbound status {inbound.status_code}: {inbound.text}")
    inbound_payload = inbound.json()
    require(inbound_payload["ok"] is True, f"inbound failed: {inbound_payload}")
    require(inbound_payload["action"] == "created", f"unexpected inbound action: {inbound_payload}")
    require(inbound_payload["dry_run"] is True, "inbound must remain dry-run in fixture verification")
    require(inbound_payload["properties"]["specification"] == "1200*600*12", f"unexpected spec: {inbound_payload}")
    require(inbound_payload["cad_fields"]["规格"] == "1200*600*12", f"unexpected CAD fields: {inbound_payload}")

    applied = deepcopy(fixture)
    applied["apply_fields"] = inbound_payload["cad_fields"]
    updated = fixture_tools.apply_fields(applied, aliases)
    require(updated == 1, f"expected only derived spec to update, got {updated}")
    require(
        applied["tables"][0][2][0] == "规格=1200*600*12",
        f"derived spec was not applied to table: {applied['tables'][0]}",
    )

    outbound = client.post(
        "/api/v1/plugins/cad-material-sync/sync/outbound",
        json={
            "profile_id": "sheet",
            "values": inbound_payload["properties"],
            "include_empty": False,
        },
    )
    require(outbound.status_code == 200, f"outbound status {outbound.status_code}: {outbound.text}")
    outbound_payload = outbound.json()
    require(outbound_payload["ok"] is True, f"outbound failed: {outbound_payload}")
    require(outbound_payload["cad_fields"]["规格"] == "1200*600*12", f"unexpected outbound CAD fields: {outbound_payload}")

    print("OK: material sync CAD fixture to Yuantus plugin e2e passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
