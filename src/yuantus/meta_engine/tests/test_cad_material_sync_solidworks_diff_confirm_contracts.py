"""Contracts for the SDK-free SolidWorks CAD material diff confirmation fixture."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "docs/samples/cad_material_solidworks_diff_confirm_fixture.json"
SCRIPT = ROOT / "scripts/verify_cad_material_solidworks_diff_confirm.py"
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
DEV_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_DIFF_CONFIRM_R1_20260511.md"
)
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
SCRIPTS_INDEX = ROOT / "docs/DELIVERY_SCRIPTS_INDEX_20260202.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_solidworks_diff_confirm_fixture_pins_write_package_contract() -> None:
    fixture = json.loads(_text(FIXTURE))
    cases = {case["name"]: case for case in fixture["cases"]}

    assert set(cases) == {
        "solidworks_sheet_add_thickness_and_change_specification",
        "solidworks_noop_requires_no_confirmation",
        "solidworks_explicit_clear_custom_property",
    }

    changed = cases["solidworks_sheet_add_thickness_and_change_specification"]
    assert changed["request"]["cad_system"] == "solidworks"
    assert changed["expect"]["summary"] == {
        "added": 1,
        "changed": 1,
        "cleared": 0,
        "unchanged": 3,
    }
    assert changed["expect"]["write_cad_fields"] == {
        "SW-Specification@Part": "1200*600*12",
        "SW-Thickness@Part": 12,
    }
    assert changed["expect"]["requires_confirmation"] is True

    noop = cases["solidworks_noop_requires_no_confirmation"]
    assert noop["expect"]["write_cad_fields"] == {}
    assert noop["expect"]["requires_confirmation"] is False

    cleared = cases["solidworks_explicit_clear_custom_property"]
    assert cleared["expect"]["write_cad_fields"] == {"SW-Coating@Part": ""}
    assert cleared["expect"]["summary"]["cleared"] == 1

    forbidden_autocad_keys = {"材料", "规格", "长", "宽", "厚", "图号", "名称"}
    for case in fixture["cases"]:
        expected = case["expect"]
        assert forbidden_autocad_keys.isdisjoint(expected["target_cad_fields"])
        assert forbidden_autocad_keys.isdisjoint(expected["write_cad_fields"])
        assert all(key.startswith("SW-") for key in expected["target_cad_fields"])
        assert all(key.startswith("SW-") for key in expected["write_cad_fields"])


def test_solidworks_diff_confirm_script_runs_without_client_dependencies() -> None:
    script = _text(SCRIPT)

    for required in (
        "cad_system",
        "solidworks",
        "cad_write_fields_from_diffs",
        "FORBIDDEN_AUTOCAD_PRIMARY_KEYS",
    ):
        assert required in script

    for forbidden in ("win32com", "pythoncom", "SldWorks.Application"):
        assert forbidden not in script

    cp = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "OK: SolidWorks CAD material diff confirm fixture passed (3 cases)" in cp.stdout


def test_solidworks_diff_confirm_todo_keeps_real_ui_incomplete() -> None:
    todo = _text(TODO)

    assert "- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" in todo
    assert (
        "  - [x] SDK-free SolidWorks `/diff/preview` 确认写回包 fixture 与 "
        "contract，固定 `SW-*@Part` 写回字段和确认边界。"
    ) in todo
    assert "  - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。" in todo
    assert "- [x] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" not in todo


def test_solidworks_diff_confirm_artifacts_are_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    scripts_index = _text(SCRIPTS_INDEX)
    ci_yml = _text(CI_YML)

    assert str(DEV_MD.relative_to(ROOT)) in doc_index
    assert "verify_cad_material_solidworks_diff_confirm.py" in scripts_index
    assert "test_cad_material_sync_solidworks_diff_confirm_contracts.py" in ci_yml
    assert str(FIXTURE.relative_to(ROOT)) in _text(DEV_MD)
    assert str(SCRIPT.relative_to(ROOT)) in _text(DEV_MD)
