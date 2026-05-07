#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PLUGIN_PATH = ROOT / "plugins" / "yuantus-cad-material-sync" / "main.py"
FIXTURE_PATH = ROOT / "docs" / "samples" / "cad_material_diff_confirm_fixture.json"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_plugin_module():
    spec = importlib.util.spec_from_file_location("cad_material_sync_plugin_contract", PLUGIN_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load plugin module from {PLUGIN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _client(module) -> TestClient:
    app = FastAPI()
    app.include_router(module.router, prefix="/api/v1")
    app.dependency_overrides[module._get_db] = lambda: object()
    app.dependency_overrides[module._current_user] = lambda: SimpleNamespace(id="contract-check")
    return TestClient(app)


def _assert_equal(case_name: str, field: str, actual, expected) -> None:
    if actual != expected:
        raise AssertionError(
            f"{case_name}: {field} mismatch\nexpected={expected!r}\nactual={actual!r}"
        )


def main() -> int:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    module = _load_plugin_module()
    client = _client(module)

    for case in fixture.get("cases") or []:
        name = case["name"]
        response = client.post(
            "/api/v1/plugins/cad-material-sync/diff/preview",
            json=case["request"],
        )
        if response.status_code != 200:
            raise AssertionError(f"{name}: expected 200, got {response.status_code}")
        payload = response.json()
        expected = case["expect"]
        for field in ("ok", "summary", "write_cad_fields", "requires_confirmation"):
            _assert_equal(name, field, payload.get(field), expected.get(field))

        diffs_by_key = {diff.get("cad_key"): diff for diff in payload.get("diffs") or []}
        for cad_key, status in (expected.get("statuses") or {}).items():
            actual = (diffs_by_key.get(cad_key) or {}).get("status")
            _assert_equal(name, f"status[{cad_key}]", actual, status)

    print(f"OK: CAD material diff confirm contract fixture passed ({len(fixture.get('cases') or [])} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
