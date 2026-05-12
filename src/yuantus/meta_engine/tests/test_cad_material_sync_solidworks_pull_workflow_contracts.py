"""Contracts for the SolidWorks CAD material pull workflow."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CLIENT = ROOT / "clients/solidworks-material-sync"
SRC = CLIENT / "SolidWorksMaterialSync"
WORKFLOW = SRC / "SolidWorksMaterialPullWorkflow.cs"
VERIFIER = CLIENT / "verify_solidworks_pull_workflow_fixture.py"
DEV_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_PULL_WORKFLOW_R1_20260512.md"
)
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_solidworks_pull_workflow_source_pins_orchestration_boundary() -> None:
    workflow = _text(WORKFLOW)

    for required in (
        "SolidWorksMaterialPullWorkflow",
        "SolidWorksMaterialFieldAdapter",
        "SolidWorksDiffPreviewClient",
        "PreviewAsync<SolidWorksDiffPreviewResult>",
        "SolidWorksDiffConfirmationViewModel.FromPreview",
        "ConfirmAndApply",
        "confirmation.Confirm()",
        "_fieldAdapter.ApplyFields",
        "Cancel(",
        "confirmation?.Cancel()",
    ):
        assert required in workflow

    assert "return 0;" in workflow
    assert "ToObjectDictionary" in workflow


def test_solidworks_pull_workflow_verifier_runs_without_windows_dependencies() -> None:
    script = _text(VERIFIER)

    for required in (
        "field snapshot -> /diff/preview -> confirmation model",
        "solidworks_sheet_add_thickness_and_change_specification",
        "solidworks_noop_requires_no_confirmation",
        "solidworks_explicit_clear_custom_property",
        "SolidWorks pull workflow fixture passed",
    ):
        assert required in script

    for forbidden in ("import win32com", "import pythoncom", "SldWorks.Application()", "subprocess.run"):
        assert forbidden not in script

    cp = subprocess.run(
        [sys.executable, str(VERIFIER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "OK: SolidWorks pull workflow fixture passed (3 cases)" in cp.stdout


def test_solidworks_pull_workflow_keeps_runtime_todo_incomplete() -> None:
    todo = _text(TODO)

    assert "- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" in todo
    assert (
        "    - [x] SDK-free SolidWorks pull workflow orchestration：串联字段快照、"
        "`/diff/preview`、确认/取消和 apply 边界。"
    ) in todo
    assert "    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。" in todo
    assert "- [x] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" not in todo


def test_solidworks_pull_workflow_artifacts_are_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    ci_yml = _text(CI_YML)
    dev_md = _text(DEV_MD)

    assert str(DEV_MD.relative_to(ROOT)) in doc_index
    assert "test_cad_material_sync_solidworks_pull_workflow_contracts.py" in ci_yml
    assert str(VERIFIER.relative_to(ROOT)) in dev_md
    assert "No WPF rendering." in dev_md
    assert "No SolidWorks COM call." in dev_md


def test_solidworks_pull_workflow_avoids_real_ui_com_and_evidence_claims() -> None:
    workflow = _text(WORKFLOW)
    dev_md = _text(DEV_MD)

    for forbidden in (
        "System.Windows",
        "SldWorks.Application",
        "CustomPropertyManager.Get6",
        "SaveAs",
        "Save3",
    ):
        assert forbidden not in workflow

    assert "No real SolidWorks UI, COM call, save/reopen persistence, or Windows evidence" in dev_md
