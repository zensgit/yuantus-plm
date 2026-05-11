"""Contracts for the P3.4 external evidence reviewer checklist."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CHECKLIST = (
    ROOT / "docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_REVIEW_CHECKLIST_20260511.md"
)
VERIFY_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_REVIEW_CHECKLIST_20260511.md"
)
REVIEWER_SOURCE = ROOT / "src/yuantus/scripts/tenant_import_rehearsal_reviewer_packet.py"
INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_review_checklist_and_verification_md_are_indexed_and_ci_wired() -> None:
    index = _text(INDEX)
    ci_yml = _text(CI_YML)

    checklist_path = str(CHECKLIST.relative_to(ROOT))
    verify_path = str(VERIFY_MD.relative_to(ROOT))

    assert checklist_path in index
    assert verify_path in index
    assert "test_p3_4_external_evidence_review_checklist_contracts.py" in ci_yml
    assert checklist_path in _text(VERIFY_MD)


def test_review_checklist_requires_complete_real_evidence_chain() -> None:
    checklist = _text(CHECKLIST)

    for artifact in (
        "output/tenant_<tenant-id>_import_rehearsal.json",
        "output/tenant_<tenant-id>_operator_rehearsal_evidence.md",
        "output/tenant_<tenant-id>_import_rehearsal_evidence_archive.json",
        "output/tenant_<tenant-id>_redaction_guard.json",
        "output/tenant_<tenant-id>_evidence_handoff.json",
        "output/tenant_<tenant-id>_evidence_intake.json",
        "output/tenant_<tenant-id>_reviewer_packet.json",
    ):
        assert artifact in checklist

    for phrase in (
        "Ready for reviewer packet: true",
        "Ready for evidence intake: true",
        "Ready for evidence handoff: true",
        "Redaction ready: true",
        "Rehearsal import passed: true",
        "Import executed: true",
        "DB connection attempted: true",
        "Rehearsal evidence accepted: true",
        "Operator evidence accepted: true",
    ):
        assert phrase in checklist


def test_review_checklist_rejects_synthetic_secrets_and_cutover_ready_artifacts() -> None:
    checklist = _text(CHECKLIST)

    for phrase in (
        "Synthetic drill output is submitted as real evidence.",
        "Ready for cutover: true",
        "Any plaintext PostgreSQL password appears",
        "Reviewer packet was generated without green evidence-intake",
        "Operator evidence has placeholder sign-off fields.",
        "Rehearsal output came from mock DSNs or a local-only drill.",
    ):
        assert phrase in checklist

    assert "Ready for cutover: false" in checklist
    assert "postgresql://<user>:***@<host>/<database>" in checklist
    assert "postgresql://source-user:" not in checklist


def test_review_checklist_does_not_authorize_phase5_or_runtime_cutover() -> None:
    checklist = _text(CHECKLIST)

    for phrase in (
        "does not by itself:",
        "start Phase 5;",
        "enable runtime `TENANCY_MODE=schema-per-tenant`;",
        "authorize production cutover;",
        "authorize production data migration;",
        "P3.4 real non-production PostgreSQL rehearsal evidence accepted.",
        "Ready for cutover remains false.",
    ):
        assert phrase in checklist


def test_reviewer_packet_source_remains_db_free_and_cutover_false() -> None:
    source = _text(REVIEWER_SOURCE)

    assert "create_engine" not in source
    assert "Session" not in source
    assert "TENANCY_MODE" not in source
    assert "build_rehearsal_evidence_archive_report" not in source
    assert "build_evidence_handoff_report" not in source
    assert '"ready_for_cutover": False' in source
