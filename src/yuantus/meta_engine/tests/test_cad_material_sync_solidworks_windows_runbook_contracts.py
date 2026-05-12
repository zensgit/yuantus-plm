"""Contracts for the SolidWorks CAD material Windows runbook."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CLIENT = ROOT / "clients/solidworks-material-sync"
GUIDE = CLIENT / "WINDOWS_SOLIDWORKS_VALIDATION_GUIDE.md"
PREFLIGHT = CLIENT / "verify_solidworks_windows_preflight.ps1"
MANIFEST = CLIENT / "MANIFEST.md"
DEV_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_RUNBOOK_R1_20260512.md"
)
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_solidworks_windows_runbook_pins_real_acceptance_path() -> None:
    guide = _text(GUIDE)

    for required in (
        "Status: template/runbook only; not validation evidence.",
        "powershell -ExecutionPolicy Bypass -File .\\verify_solidworks_windows_preflight.ps1",
        "SolidWorks Load Smoke",
        "Field Read Smoke",
        "Diff Preview And Confirmation Smoke",
        "Save/Reopen Persistence Smoke",
        "Evidence Validation",
        "scripts\\validate_cad_material_solidworks_windows_evidence.py",
        "OK: CAD material SolidWorks Windows evidence shape is acceptable",
        "Do not mark SolidWorks field reading, local confirmation UI, COM write-back, or\nWindows runtime acceptance complete from this guide alone.",
    ):
        assert required in guide


def test_solidworks_windows_preflight_checks_expected_tools_and_paths() -> None:
    preflight = _text(PREFLIGHT)

    for required in (
        "param(",
        "$SolidWorksInstallDir",
        "$ProjectPath",
        "$OutputDll",
        "$RunBuild",
        "SLDWORKS.exe",
        "WINDOWS_SOLIDWORKS_VALIDATION_GUIDE.md",
        "MANIFEST.md",
        "msbuild.exe",
        "MSBuild found",
        "SolidWorksMaterialSync",
        "Preflight passed. The Windows machine is ready for SolidWorks material sync build/smoke.",
    ):
        assert required in preflight

    for forbidden in ("token", "password", "secret", "Invoke-WebRequest"):
        assert forbidden not in preflight.lower()


def test_solidworks_windows_runbook_keeps_runtime_todo_incomplete() -> None:
    todo = _text(TODO)
    guide = _text(GUIDE)

    assert "- [ ] SolidWorks 明细表/属性表字段读取。" in todo
    assert "- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" in todo
    assert "    - [ ] 真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。" in todo
    assert "    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。" in todo
    assert "- [x] SolidWorks 明细表/属性表字段读取。" not in todo
    assert "- [x] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" not in todo
    assert "No real Add-in/COM implementation." in _text(DEV_MD)
    assert "No filled evidence file." in _text(DEV_MD)
    assert "No TODO parent completion." in _text(DEV_MD)
    assert "No compiled DLL" in guide


def test_solidworks_windows_runbook_artifacts_are_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    ci_yml = _text(CI_YML)
    manifest = _text(MANIFEST)
    dev_md = _text(DEV_MD)

    assert str(DEV_MD.relative_to(ROOT)) in doc_index
    assert "test_cad_material_sync_solidworks_windows_runbook_contracts.py" in ci_yml
    assert "WINDOWS_SOLIDWORKS_VALIDATION_GUIDE.md" in manifest
    assert "verify_solidworks_windows_preflight.ps1" in manifest
    assert str(GUIDE.relative_to(ROOT)) in dev_md
    assert str(PREFLIGHT.relative_to(ROOT)) in dev_md
