"""Contracts for SolidWorks CAD material Windows evidence gating."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
TEMPLATE = (
    ROOT / "docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md"
)
VALIDATOR = ROOT / "scripts/validate_cad_material_solidworks_windows_evidence.py"
DEV_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_EVIDENCE_TEMPLATE_20260511.md"
)
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
SCRIPTS_INDEX = ROOT / "docs/DELIVERY_SCRIPTS_INDEX_20260202.md"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_solidworks_windows_evidence_template_is_blank_and_not_acceptance() -> None:
    template = _text(TEMPLATE)

    for phrase in (
        "Status: **template only; not validation evidence**",
        "Do not mark SolidWorks field\nreading, local confirmation UI, COM write-back, or Windows runtime acceptance\ncomplete",
        "SolidWorks field read complete: no",
        "SolidWorks local confirmation UI complete: no",
        "Real SolidWorks write-back validated: no",
        "Windows SolidWorks runtime accepted: no",
        "SolidWorks regression complete: no",
        "Decision: pending",
        "must remain `no` and the decision must remain `pending`",
        "Property read evidence uses a mock fixture or synthetic output.",
        "The saved SolidWorks document was not reopened to confirm persistence.",
        "python3 scripts/validate_cad_material_solidworks_windows_evidence.py",
        "Real SolidWorks Add-in/COM field reading evidence is not recorded.",
        "Real SolidWorks local confirmation UI and write-back evidence is not recorded.",
    ):
        assert phrase in template

    for forbidden in (
        "SolidWorks field read complete: yes\n",
        "SolidWorks local confirmation UI complete: yes\n",
        "Real SolidWorks write-back validated: yes\n",
        "Windows SolidWorks runtime accepted: yes\n",
        "SolidWorks regression complete: yes\n",
        "Decision: accept\n",
    ):
        assert forbidden not in template


def _minimal_real_solidworks_evidence(*, regression_complete: bool = False) -> str:
    regression_result = "yes" if regression_complete else "no"
    regression_fields = {
        "SolidWorks regression version": "SolidWorks 2025",
        "SolidWorks regression service pack": "SP1",
        "SolidWorks regression build result": "passed",
        "SolidWorks regression load result": "passed",
        "SolidWorks regression field read result": "passed",
        "SolidWorks regression write-back result": "passed",
    }
    if not regression_complete:
        regression_fields = {key: "" for key in regression_fields}

    lines = [
        "# Filled SolidWorks CAD Material Sync Windows Evidence",
        "Operator: reviewer-one",
        "Review date: 2026-05-11",
        "Windows version: Windows 11 x64",
        "SolidWorks primary version: SolidWorks 2024",
        "SolidWorks service pack: SP5",
        "Yuantus base URL: http://127.0.0.1:7910",
        "Yuantus commit: 14d89e3",
        "Test SolidWorks document description: sanitized-test-part.sldprt",
        "Build command: msbuild SolidWorksMaterialSyncAddin.csproj /p:Configuration=Release",
        "Build result: passed",
        "Compiled add-in DLL path: evidence/SolidWorksMaterialSyncAddin.dll",
        "Add-in manifest or registration path: evidence/addin-registration.reg",
        "Load method: add-in manager",
        "Loaded add-in path: evidence/SolidWorksMaterialSyncAddin.dll",
        "SolidWorks add-in load result: passed",
        "SolidWorks add-in log path: evidence/solidworks-addin.log",
        "Profile fetch result: passed",
        "Property read command result: passed",
        "Diff preview UI result: passed",
        "Confirm write command result: passed",
        "Cancel path result: passed",
        "SolidWorks document description: sanitized-test-part.sldprt",
        "Custom property read result: passed",
        "Cut-list or table read result: passed",
        "Read SW-Material@Part value: Q235B",
        "Read SW-Specification@Part value: old-spec",
        "Read SW-Length@Part or @CutList value: 1200",
        "Read SW-Width@Part or @CutList value: 600",
        "Read SW-Thickness@Part value: 12",
        "Before SW-Material@Part value: Q235B",
        "Before SW-Specification@Part value: old-spec",
        "Diff preview screenshot path: evidence/solidworks-diff-preview.png",
        "Write package JSON path: evidence/solidworks-write-package.json",
        "User action: confirm",
        "After SW-Material@Part value: Q235B",
        "After SW-Specification@Part value: 1200*600*12",
        "Save/reopen result: passed and persisted",
        "Yuantus dry-run log path: evidence/dry-run.log",
        "Yuantus real-write log path: evidence/real-write.log",
        "SolidWorks regression installed: no",
        f"SolidWorks regression version: {regression_fields['SolidWorks regression version']}",
        f"SolidWorks regression service pack: {regression_fields['SolidWorks regression service pack']}",
        f"SolidWorks regression build result: {regression_fields['SolidWorks regression build result']}",
        f"SolidWorks regression load result: {regression_fields['SolidWorks regression load result']}",
        f"SolidWorks regression field read result: {regression_fields['SolidWorks regression field read result']}",
        f"SolidWorks regression write-back result: {regression_fields['SolidWorks regression write-back result']}",
        "SolidWorks field read complete: yes",
        "SolidWorks local confirmation UI complete: yes",
        "Real SolidWorks write-back validated: yes",
        "Windows SolidWorks runtime accepted: yes",
        f"SolidWorks regression complete: {regression_result}",
        "Reviewer: reviewer-two",
        "Decision date: 2026-05-11",
        "Decision: accept",
        "Reason: real Windows SolidWorks evidence reviewed",
    ]
    return "\n".join(lines) + "\n"


def _run_validator(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_solidworks_windows_evidence_validator_rejects_blank_template() -> None:
    cp = _run_validator(TEMPLATE)

    assert cp.returncode == 1
    assert "FAIL: CAD material SolidWorks Windows evidence is not acceptable" in cp.stdout
    assert "SolidWorks field read complete must be yes" in cp.stdout
    assert "Decision must be accept after reviewer approval" in cp.stdout


def test_solidworks_windows_evidence_validator_accepts_minimal_real_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "filled-solidworks-windows-evidence.md"
    evidence.write_text(_minimal_real_solidworks_evidence(), encoding="utf-8")

    cp = _run_validator(evidence)

    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert "OK: CAD material SolidWorks Windows evidence shape is acceptable" in cp.stdout


def test_solidworks_windows_evidence_validator_rejects_incomplete_regression_claim(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "filled-solidworks-windows-evidence.md"
    evidence.write_text(
        _minimal_real_solidworks_evidence().replace(
            "SolidWorks regression complete: no",
            "SolidWorks regression complete: yes",
        ),
        encoding="utf-8",
    )

    cp = _run_validator(evidence)

    assert cp.returncode == 1
    assert "SolidWorks regression version must be filled" in cp.stdout
    assert "SolidWorks regression write-back result must be filled" in cp.stdout


def test_solidworks_windows_evidence_validator_json_output_is_redaction_safe(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "secret-bearing-solidworks-windows-evidence.md"
    evidence.write_text(
        _minimal_real_solidworks_evidence().replace(
            "Yuantus real-write log path: evidence/real-write.log",
            "Yuantus real-write log path: token=SUPERSECRET123",
        ),
        encoding="utf-8",
    )

    cp = _run_validator(evidence, "--json")

    assert cp.returncode == 1
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == 1
    assert payload["ok"] is False
    assert payload["failure_count"] == 1
    assert payload["failures"] == [
        "Yuantus real-write log path appears to contain a plaintext secret"
    ]
    assert "SUPERSECRET123" not in cp.stdout
    assert "token=" not in cp.stdout


def test_solidworks_windows_evidence_validator_rejects_mock_fixture_evidence(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "mock-solidworks-windows-evidence.md"
    evidence.write_text(
        _minimal_real_solidworks_evidence().replace(
            "Custom property read result: passed",
            "Custom property read result: mock fixture passed",
        ),
        encoding="utf-8",
    )

    cp = _run_validator(evidence)

    assert cp.returncode == 1
    assert "Custom property read result appears to contain non-real evidence: mock fixture" in cp.stdout


def test_solidworks_windows_evidence_todo_keeps_real_work_incomplete() -> None:
    todo = _text(TODO)

    assert (
        "    - [x] SolidWorks Windows evidence 模板与 validator，固定真实 Add-in/COM/"
        "确认 UI smoke 的验收字段。"
    ) in todo
    assert "    - [ ] 真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。" in todo
    assert "    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。" in todo
    assert "- [x] SolidWorks 明细表/属性表字段读取。" not in todo
    assert "- [x] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" not in todo


def test_solidworks_windows_evidence_artifacts_are_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    scripts_index = _text(SCRIPTS_INDEX)
    ci_yml = _text(CI_YML)

    assert str(TEMPLATE.relative_to(ROOT)) in doc_index
    assert str(DEV_MD.relative_to(ROOT)) in doc_index
    assert "validate_cad_material_solidworks_windows_evidence.py" in scripts_index
    assert "test_cad_material_sync_solidworks_windows_evidence_contracts.py" in ci_yml
    assert str(TEMPLATE.relative_to(ROOT)) in _text(DEV_MD)
    assert str(VALIDATOR.relative_to(ROOT)) in _text(DEV_MD)
