"""Contracts for the SolidWorks external Windows validation handoff."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
HANDOFF = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_EXTERNAL_HANDOFF_20260512.md"
)
TASKBOOK = (
    ROOT
    / "docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_SOLIDWORKS_CLIENT_R1_20260512.md"
)
WINDOWS_GUIDE = ROOT / "clients/solidworks-material-sync/WINDOWS_SOLIDWORKS_VALIDATION_GUIDE.md"
PREFLIGHT = ROOT / "clients/solidworks-material-sync/verify_solidworks_windows_preflight.ps1"
EVIDENCE_TEMPLATE = (
    ROOT / "docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md"
)
VALIDATOR = ROOT / "scripts/validate_cad_material_solidworks_windows_evidence.py"
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_solidworks_external_handoff_references_canonical_inputs() -> None:
    handoff = _text(HANDOFF)

    for path in (
        TASKBOOK,
        WINDOWS_GUIDE,
        PREFLIGHT,
        EVIDENCE_TEMPLATE,
        VALIDATOR,
    ):
        assert str(path.relative_to(ROOT)) in handoff

    for phrase in (
        "handoff/launchpack only",
        "not implement real\nSolidWorks runtime support",
        "not Windows\nacceptance evidence",
        "No filled evidence file.",
        "No replacement for Windows + SolidWorks manual validation.",
    ):
        assert phrase in handoff


def test_solidworks_external_handoff_pins_operator_commands_and_artifacts() -> None:
    handoff = _text(HANDOFF)

    for phrase in (
        "powershell -ExecutionPolicy Bypass -File .\\verify_solidworks_windows_preflight.ps1",
        "python scripts\\validate_cad_material_solidworks_windows_evidence.py",
        "preflight output",
        "SolidWorks version",
        "SolidWorks service pack",
        "build result",
        "Add-in/COM load result",
        "custom property read result",
        "cut-list or table field read result",
        "diff preview UI result",
        "cancel path result",
        "confirm write result",
        "save/reopen result",
        "validator OK output",
        "OK: CAD material SolidWorks Windows evidence shape is acceptable",
    ):
        assert phrase in handoff


def test_solidworks_external_handoff_pins_redaction_and_stop_gates() -> None:
    handoff = _text(HANDOFF)

    for phrase in (
        "plaintext secrets",
        "bearer tokens",
        "tenant tokens",
        "workstation usernames",
        "production CAD file paths",
        "customer names",
        "any preflight step fails",
        "real SolidWorks installation",
        "Add-in/COM load is not demonstrated",
        "custom property read uses a mock, fixture, or SDK-free contract output",
        "diff preview UI is not shown",
        "cancel path is not demonstrated",
        "confirm write is not demonstrated",
        "save/reopen persistence is missing",
        "validate_cad_material_solidworks_windows_evidence.py` fails",
        "TODO parent items are marked complete from this handoff alone",
    ):
        assert phrase in handoff


def test_solidworks_external_handoff_keeps_real_todo_items_unchecked() -> None:
    todo = _text(TODO)
    handoff = _text(HANDOFF)

    assert "- [ ] SolidWorks 明细表/属性表字段读取。" in todo
    assert "- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" in todo
    assert "    - [ ] 真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。" in todo
    assert "    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。" in todo
    assert "- [x] SolidWorks 明细表/属性表字段读取。" not in todo
    assert "- [x] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" not in todo

    for phrase in (
        "SolidWorks 明细表/属性表字段读取。",
        "真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。",
        "SolidWorks 本地客户端可视化差异预览和确认写回 UI。",
        "真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。",
    ):
        assert phrase in handoff


def test_solidworks_external_handoff_is_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    ci_yml = _text(CI_YML)

    assert str(HANDOFF.relative_to(ROOT)) in doc_index
    assert "test_cad_material_sync_solidworks_external_handoff_contracts.py" in ci_yml
