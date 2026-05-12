#!/usr/bin/env python3
"""Verify the SDK-free SolidWorks diff confirmation fixture."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PLUGIN_PATH = ROOT / "plugins" / "yuantus-cad-material-sync" / "main.py"
FIXTURE_PATH = ROOT / "docs" / "samples" / "cad_material_solidworks_diff_confirm_fixture.json"

FORBIDDEN_AUTOCAD_PRIMARY_KEYS = {
    "图号",
    "名称",
    "材料",
    "材质",
    "规格",
    "物料规格",
    "长",
    "长度",
    "宽",
    "宽度",
    "厚",
    "厚度",
}

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _load_plugin_module():
    spec = importlib.util.spec_from_file_location("cad_material_sync_solidworks_diff", PLUGIN_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load plugin module from {PLUGIN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assert_equal(case_name: str, field: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise AssertionError(
            f"{case_name}: {field} mismatch\nexpected={expected!r}\nactual={actual!r}"
        )


def _assert_solidworks_keys(case_name: str, fields: dict[str, Any], *, allow_empty: bool = True) -> None:
    forbidden = sorted(FORBIDDEN_AUTOCAD_PRIMARY_KEYS & set(fields))
    if forbidden:
        raise AssertionError(
            f"{case_name}: SolidWorks package used AutoCAD primary keys: {forbidden!r}"
        )
    invalid = sorted(
        key
        for key, value in fields.items()
        if (allow_empty or str(value).strip()) and (not key.startswith("SW-") or "@Part" not in key)
    )
    if invalid:
        raise AssertionError(f"{case_name}: non-SolidWorks fields in package: {invalid!r}")


def _preview_payload(module, fixture: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    request = case["request"]
    cad_system = request.get("cad_system")
    profiles = module.load_profiles(config=fixture.get("profile_config") or {})
    profile = module._get_profile(profiles, request.get("profile_id"))

    target_values = dict(request.get("target_properties") or {})
    target_values.update(request.get("values") or {})
    has_structured_target = bool(target_values)

    if has_structured_target and request.get("target_cad_fields"):
        target_values.update(
            module.cad_fields_to_properties(profile, request.get("target_cad_fields") or {})
        )

    if has_structured_target:
        properties, _composed, errors, warnings = module.compose_profile(profile, target_values)
        target_cad_fields = module.cad_field_package(
            profile,
            properties,
            include_empty=bool(request.get("include_empty", False)),
            cad_system=cad_system,
        )
        target_cad_fields.update(request.get("target_cad_fields") or {})
    else:
        properties = module.cad_fields_to_properties(profile, request.get("target_cad_fields") or {})
        errors = []
        warnings = []
        target_cad_fields = dict(request.get("target_cad_fields") or {})

    diffs, summary, current_package = module.build_cad_field_diff(
        profile,
        current_cad_fields=request.get("current_cad_fields") or {},
        target_cad_fields=target_cad_fields,
        cad_system=cad_system,
    )
    write_cad_fields = module.cad_write_fields_from_diffs(diffs)
    return {
        "ok": not errors,
        "properties": properties,
        "target_cad_fields": target_cad_fields,
        "current_cad_fields": current_package,
        "write_cad_fields": write_cad_fields,
        "requires_confirmation": bool(write_cad_fields),
        "diffs": diffs,
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
    }


def verify_fixture(path: Path) -> None:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    module = _load_plugin_module()

    for case in fixture.get("cases") or []:
        name = case["name"]
        payload = _preview_payload(module, fixture, case)
        expected = case["expect"]
        for field in (
            "ok",
            "summary",
            "target_cad_fields",
            "write_cad_fields",
            "requires_confirmation",
        ):
            _assert_equal(name, field, payload.get(field), expected.get(field))

        _assert_solidworks_keys(name, payload["target_cad_fields"])
        _assert_solidworks_keys(name, payload["write_cad_fields"])

        diffs_by_key = {diff.get("cad_key"): diff for diff in payload.get("diffs") or []}
        for cad_key, status in (expected.get("statuses") or {}).items():
            actual = (diffs_by_key.get(cad_key) or {}).get("status")
            _assert_equal(name, f"status[{cad_key}]", actual, status)


def main() -> int:
    try:
        verify_fixture(FIXTURE_PATH)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    print(
        "OK: SolidWorks CAD material diff confirm fixture passed "
        f"({len(fixture.get('cases') or [])} cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
