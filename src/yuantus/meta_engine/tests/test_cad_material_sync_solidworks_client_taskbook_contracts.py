"""Contracts for the SolidWorks CAD material client implementation taskbook."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
TASKBOOK = (
    ROOT
    / "docs/DEVELOPMENT_CLAUDE_TASK_CAD_MATERIAL_SYNC_SOLIDWORKS_CLIENT_R1_20260512.md"
)
DEV_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_SOLIDWORKS_CLIENT_TASKBOOK_20260512.md"
)
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_solidworks_client_taskbook_pins_real_client_scope() -> None:
    taskbook = _text(TASKBOOK)

    for required in (
        "clients/solidworks-material-sync/",
        "CustomPropertyManager",
        "Get6",
        "GetAll3",
        "cut-list or table",
        "/api/v1/plugins/cad-material-sync/diff/preview",
        "cad_system=solidworks",
        "write_cad_fields",
        "scripts/validate_cad_material_solidworks_windows_evidence.py",
        "SolidWorks Add-in/COM",
        "Save and reopen",
    ):
        assert required in taskbook


def test_solidworks_client_taskbook_forbids_false_acceptance_paths() -> None:
    taskbook = _text(TASKBOOK)

    for required in (
        "Generated binary artifacts",
        "Secrets, bearer tokens",
        "Marking the SolidWorks TODO parent items complete without accepted real Windows evidence",
        "Mock fixture output represented as real SolidWorks evidence",
        "No claim that Windows smoke is complete from macOS-only tests",
    ):
        assert required in taskbook

    assert "compiled DLLs, logs, screenshots, or CAD sample\n  files committed" in taskbook


def test_solidworks_client_taskbook_keeps_todo_parent_items_unchecked() -> None:
    todo = _text(TODO)

    assert "- [ ] SolidWorks 明细表/属性表字段读取。" in todo
    assert "    - [ ] 真实 SolidWorks Add-in/COM 读取实现与 Windows smoke。" in todo
    assert "- [ ] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" in todo
    assert "    - [ ] 真实 SolidWorks 本地确认 UI、COM 写回和 Windows smoke。" in todo

    assert "- [x] SolidWorks 明细表/属性表字段读取。" not in todo
    assert "- [x] SolidWorks 本地客户端可视化差异预览和确认写回 UI。" not in todo


def test_solidworks_client_taskbook_verification_md_records_commands() -> None:
    dev_md = _text(DEV_MD)

    assert str(TASKBOOK.relative_to(ROOT)) in dev_md
    assert "test_cad_material_sync_solidworks_client_taskbook_contracts.py" in dev_md
    assert "test_cad_material_sync_solidworks_fixture_contracts.py" in dev_md
    assert "test_cad_material_sync_solidworks_diff_confirm_contracts.py" in dev_md
    assert "test_cad_material_sync_solidworks_windows_evidence_contracts.py" in dev_md
    assert "test_dev_and_verification_doc_index_completeness.py" in dev_md
    assert "test_ci_contracts_ci_yml_test_list_order.py" in dev_md
    assert "git diff --check" in dev_md
    assert "No `clients/solidworks-material-sync/` runtime code." in dev_md


def test_solidworks_client_taskbook_artifacts_are_indexed_and_ci_wired() -> None:
    doc_index = _text(DOC_INDEX)
    ci_yml = _text(CI_YML)

    assert str(TASKBOOK.relative_to(ROOT)) in doc_index
    assert str(DEV_MD.relative_to(ROOT)) in doc_index
    assert "test_cad_material_sync_solidworks_client_taskbook_contracts.py" in ci_yml
