"""Contracts for CAD material sync external Windows validation handoff."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
HANDOFF = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_EXTERNAL_VALIDATION_HANDOFF_20260511.md"
)
EVIDENCE_TEMPLATE = (
    ROOT / "docs/CAD_MATERIAL_SYNC_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md"
)
EVIDENCE_TEMPLATE_DV = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CAD_MATERIAL_SYNC_WINDOWS_EVIDENCE_TEMPLATE_20260511.md"
)
TODO = ROOT / "docs/TODO_CAD_MATERIAL_SYNC_PLUGIN_20260506.md"
WINDOWS_GUIDE = (
    ROOT / "clients/autocad-material-sync/WINDOWS_AUTOCAD2018_VALIDATION_GUIDE.md"
)
INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_external_validation_handoff_records_post_merge_boundary() -> None:
    handoff = _text(HANDOFF)

    for phrase in (
        "PR #495 merged the CAD Material Sync delivery package on `main=8593911`.",
        "remaining validation is external: Windows + AutoCAD 2018 DLL loading and real\nDWG write-back smoke",
        "not replaced by macOS/Linux\nfixture, SQLite, Playwright, or packaging checks",
        "Windows + AutoCAD 2018 real smoke: pending.",
        "Windows + AutoCAD 2024 regression smoke: pending.",
        "It is not itself the Windows validation result.",
        "No fake or synthetic Windows evidence.",
        "No Phase 5 implementation.",
        "No P3.4 evidence creation or acceptance.",
    ):
        assert phrase in handoff

    for forbidden in (
        "AutoCAD 2018 support complete: true",
        "Real DWG write-back validated: true",
        "Windows client runtime accepted: true",
    ):
        assert forbidden not in handoff


def test_todo_keeps_external_windows_smokes_unchecked() -> None:
    todo = _text(TODO)

    assert "- [ ] 在 Windows + AutoCAD 2018 环境编译 DLL 并做真实 DWG 手工 smoke。" in todo
    assert "- [ ] 在 Windows + AutoCAD 2024 环境做回归 smoke，确保高版本路径未退化。" in todo
    assert "- [x] 在 Windows + AutoCAD 2018 环境编译 DLL 并做真实 DWG 手工 smoke。" not in todo
    assert "- [x] 在 Windows + AutoCAD 2024 环境做回归 smoke，确保高版本路径未退化。" not in todo


def test_windows_validation_guide_preserves_required_evidence_and_exit_criteria() -> None:
    guide = _text(WINDOWS_GUIDE)

    for phrase in (
        "This guide does not replace macOS-side service, fixture, or contract tests.",
        "AutoCAD `ACADVER` output showing `R22.0`.",
        "Preflight output.",
        "Build output and DLL path.",
        "Screenshot or command log for `DEDUPHELP`, `PLMMATPROFILES`, `PLMMATCOMPOSE`, `PLMMATPUSH`, `PLMMATPULL`.",
        "Before/after screenshot of the DWG material field.",
        "Preflight passes on the Windows machine.",
        "DLL builds against AutoCAD 2018 assemblies.",
        "AutoCAD 2018 loads the plugin.",
        "A real DWG title block or table field is updated and persists after save/reopen.",
    ):
        assert phrase in guide


def test_windows_evidence_template_is_blank_and_not_acceptance() -> None:
    template = _text(EVIDENCE_TEMPLATE)

    for phrase in (
        "Status: **template only; not validation evidence**",
        "Do not mark the Windows validation complete\nuntil this template is filled with real operator output and reviewed.",
        "AutoCAD primary version: `2018`",
        "AutoCAD ACADVER output: `R22.0`",
        "AutoCAD regression version: `2024`",
        "AutoCAD 2018 support complete: no",
        "Real DWG write-back validated: no",
        "Windows client runtime accepted: no",
        "AutoCAD 2024 regression complete: no",
        "Decision: pending",
        "must remain `no` and the decision must remain `pending`",
        "The DWG write-back result uses a mock fixture instead of a real DWG.",
        "The saved DWG was not reopened to confirm persistence.",
        "Any plaintext token, password, or production customer drawing content appears\n  in the evidence.",
        "Windows + AutoCAD 2018 evidence is not recorded.",
        "AutoCAD 2024 regression evidence is not recorded.",
    ):
        assert phrase in template

    for forbidden in (
        "AutoCAD 2018 support complete: yes\n",
        "Real DWG write-back validated: yes\n",
        "Windows client runtime accepted: yes\n",
        "AutoCAD 2024 regression complete: yes\n",
        "Decision: accept\n",
    ):
        assert forbidden not in template


def test_external_validation_handoff_is_indexed_and_ci_wired() -> None:
    index = _text(INDEX)
    ci_yml = _text(CI_YML)
    handoff_doc = str(HANDOFF.relative_to(ROOT))
    template_doc = str(EVIDENCE_TEMPLATE.relative_to(ROOT))
    template_dv_doc = str(EVIDENCE_TEMPLATE_DV.relative_to(ROOT))

    assert handoff_doc in index
    assert template_doc in index
    assert template_dv_doc in index
    assert handoff_doc in _text(HANDOFF)
    assert template_dv_doc in _text(EVIDENCE_TEMPLATE_DV)
    assert "test_cad_material_sync_external_validation_contracts.py" in ci_yml
