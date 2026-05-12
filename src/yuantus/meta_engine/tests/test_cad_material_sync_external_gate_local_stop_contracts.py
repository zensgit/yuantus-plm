"""Contracts for CAD Material Sync external-gate local stop."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
STOP_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_EXTERNAL_GATE_LOCAL_STOP_20260512.md"
)
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
AUTOCAD_HANDOFF = (
    ROOT / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_EXTERNAL_VALIDATION_HANDOFF_20260511.md"
)
AUTOCAD_EVIDENCE = ROOT / "docs/CAD_MATERIAL_SYNC_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md"
AUTOCAD_VALIDATOR = ROOT / "scripts/validate_cad_material_windows_evidence.py"
SOLIDWORKS_HANDOFF = (
    ROOT / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_EXTERNAL_HANDOFF_20260512.md"
)
SOLIDWORKS_EVIDENCE = (
    ROOT / "docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md"
)
SOLIDWORKS_VALIDATOR = ROOT / "scripts/validate_cad_material_solidworks_windows_evidence.py"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cad_material_sync_external_gate_references_canonical_inputs() -> None:
    stop_md = _text(STOP_MD)

    for path in (
        TODO,
        AUTOCAD_HANDOFF,
        AUTOCAD_EVIDENCE,
        AUTOCAD_VALIDATOR,
        SOLIDWORKS_HANDOFF,
        SOLIDWORKS_EVIDENCE,
        SOLIDWORKS_VALIDATOR,
    ):
        assert str(path.relative_to(ROOT)) in stop_md

    for phrase in (
        "local stop point for the CAD Material Sync line",
        "remaining work requires real Windows CAD operator\nexecution",
        "Do not mark the CAD Material Sync TODO parents complete from local tests",
        "not another macOS/local\nimplementation slice",
    ):
        assert phrase in stop_md


def test_cad_material_sync_external_gate_keeps_remaining_todos_unchecked() -> None:
    todo = _text(TODO)
    stop_md = _text(STOP_MD)

    unchecked_items = (
        "- [ ] CAD 客户端适配层：",
        "  - [ ] SolidWorks 明细表/属性表字段读取。",
        "    - [ ] 真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。",
        "  - [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。",
        "    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。",
        "- [ ] 更完整验证：",
        "  - [ ] 在 Windows + AutoCAD 2018 环境编译 DLL 并做真实 DWG 手工 smoke。",
        "  - [ ] 在 Windows + AutoCAD 2024 环境做回归 smoke，确保高版本路径未退化。",
    )
    checked_forbidden = tuple(item.replace("[ ]", "[x]") for item in unchecked_items)

    for item in unchecked_items:
        assert item in todo

    for item in checked_forbidden:
        assert item not in todo

    for phrase in (
        "CAD 客户端适配层",
        "SolidWorks 明细表/属性表字段读取。",
        "真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。",
        "SolidWorks 本地客户端可视化差异预览和确认写回 UI。",
        "真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。",
        "更完整验证",
        "在 Windows + AutoCAD 2018 环境编译 DLL 并做真实 DWG 手工 smoke。",
        "在 Windows + AutoCAD 2024 环境做回归 smoke，确保高版本路径未退化。",
    ):
        assert phrase in stop_md


def test_cad_material_sync_external_gate_pins_allowed_next_pr_shapes() -> None:
    stop_md = _text(STOP_MD)

    for phrase in (
        "AutoCAD evidence signoff PR",
        "validate_cad_material_windows_evidence.py",
        "SolidWorks evidence signoff PR",
        "validate_cad_material_solidworks_windows_evidence.py",
        "Real SolidWorks implementation PR",
        "Windows + SolidWorks-capable environment",
        "Independent triggered taskbook",
        "names the new trigger, scope, non-goals, and verification plan",
    ):
        assert phrase in stop_md


def test_cad_material_sync_external_gate_pins_stop_gates_and_non_goals() -> None:
    stop_md = _text(STOP_MD)

    for phrase in (
        "no Windows workstation is available",
        "no AutoCAD 2018 installation is available",
        "no AutoCAD 2024 installation is available",
        "no SolidWorks installation is available",
        "mock, fixture, or SDK-free output",
        "evidence validator output is missing or failing",
        "plaintext secrets",
        "production CAD paths",
        "unredacted customer drawing content",
        "No runtime code changes.",
        "No AutoCAD or SolidWorks binary artifact.",
        "No mock evidence acceptance.",
        "No TODO parent completion.",
        "No Phase 5 implementation.",
        "No P3.4 evidence creation or acceptance.",
    ):
        assert phrase in stop_md


def test_cad_material_sync_external_gate_is_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    ci_yml = _text(CI_YML)

    assert str(STOP_MD.relative_to(ROOT)) in doc_index
    assert "test_cad_material_sync_external_gate_local_stop_contracts.py" in ci_yml
