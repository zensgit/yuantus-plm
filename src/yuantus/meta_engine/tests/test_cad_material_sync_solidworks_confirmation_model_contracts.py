"""Contracts for the SolidWorks CAD material confirmation model."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CLIENT = ROOT / "clients/solidworks-material-sync"
SRC = CLIENT / "SolidWorksMaterialSync"
MODEL = SRC / "SolidWorksDiffConfirmationViewModel.cs"
VERIFIER = CLIENT / "verify_solidworks_confirmation_fixture.py"
FIXTURE = ROOT / "docs/samples/cad_material_solidworks_diff_confirm_fixture.json"
DEV_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_CONFIRMATION_MODEL_R1_20260512.md"
)
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_confirmation_model_source_pins_confirm_cancel_boundary() -> None:
    model = _text(MODEL)

    for required in (
        "SolidWorksDiffConfirmationViewModel",
        "FromPreview",
        "SolidWorksDiffPreviewResult",
        "SolidWorksDiffFieldRow",
        "Confirm()",
        "Cancel()",
        "ConfirmedWriteFields",
        "RequiresConfirmation",
        "SolidWorksWriteBackPlan.FromWriteCadFields",
    ):
        assert required in model

    assert "IsCancelled = true" in model
    assert "new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)" in model


def test_confirmation_fixture_verifier_runs_without_solidworks_or_dotnet() -> None:
    script = _text(VERIFIER)

    for required in (
        "docs/samples/cad_material_solidworks_diff_confirm_fixture.json",
        "confirmed_write_fields",
        "cancel should be no-op",
        "SolidWorks confirmation fixture passed",
    ):
        assert required in script

    for forbidden in ("win32com", "pythoncom", "SldWorks.Application", "dotnet"):
        assert forbidden not in script

    cp = subprocess.run(
        [sys.executable, str(VERIFIER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "OK: SolidWorks confirmation fixture passed (3 cases)" in cp.stdout


def test_confirmation_model_matches_fixture_confirm_cancel_and_noop() -> None:
    fixture = json.loads(_text(FIXTURE))
    cases = {case["name"]: case for case in fixture["cases"]}

    changed = cases["solidworks_sheet_add_thickness_and_change_specification"]
    assert changed["expect"]["requires_confirmation"] is True
    assert changed["expect"]["write_cad_fields"] == {
        "SW-Specification@Part": "1200*600*12",
        "SW-Thickness@Part": 12,
    }
    assert changed["expect"]["statuses"]["SW-Thickness@Part"] == "added"
    assert changed["expect"]["statuses"]["SW-Specification@Part"] == "changed"

    noop = cases["solidworks_noop_requires_no_confirmation"]
    assert noop["expect"]["requires_confirmation"] is False
    assert noop["expect"]["write_cad_fields"] == {}

    cleared = cases["solidworks_explicit_clear_custom_property"]
    assert cleared["expect"]["requires_confirmation"] is True
    assert cleared["expect"]["write_cad_fields"] == {"SW-Coating@Part": ""}
    assert cleared["expect"]["statuses"]["SW-Coating@Part"] == "cleared"


def test_confirmation_model_todo_tracks_sdk_free_substep_only() -> None:
    todo = _text(TODO)

    assert "- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" in todo
    assert (
        "    - [x] SDK-free SolidWorks confirmation view-model：固定确认、"
        "取消/no-op、显式清空和 `write_cad_fields` 过滤。"
    ) in todo
    assert "    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。" in todo
    assert "- [x] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" not in todo


def test_confirmation_model_artifacts_are_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    ci_yml = _text(CI_YML)
    dev_md = _text(DEV_MD)

    assert str(DEV_MD.relative_to(ROOT)) in doc_index
    assert "test_cad_material_sync_solidworks_confirmation_model_contracts.py" in ci_yml
    assert str(VERIFIER.relative_to(ROOT)) in dev_md
    assert "No WPF window or Windows UI rendering." in dev_md
