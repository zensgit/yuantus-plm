"""Contracts for the P3.4 external evidence readiness closeout status."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
STATUS = ROOT / "docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_20260430.md"
TODO = ROOT / "docs/PHASE3_TENANT_IMPORT_READINESS_STATUS_TODO_20260430.md"
VERIFY_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_READINESS_CLOSEOUT_20260511.md"
)
INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readiness_status_records_post_p6_handoff_and_review_docs() -> None:
    status = _text(STATUS)

    for phrase in (
        "2026-05-11 update: post-P6 external evidence handoff is now explicit",
        "docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_HANDOFF_PACKET_20260511.md",
        "docs/PHASE3_TENANT_IMPORT_EXTERNAL_EVIDENCE_REVIEW_CHECKLIST_20260511.md",
        "These documents close the remaining local handoff/documentation gap only.",
        "do not provide operator-run PostgreSQL evidence",
        "do not unblock Phase 5 without accepted real evidence",
    ):
        assert phrase in status


def test_readiness_todo_keeps_external_evidence_and_acceptance_unchecked() -> None:
    todo = _text(TODO)

    for phrase in (
        "- [x] Track post-P6 external evidence handoff packet as local documentation only.",
        "- [x] Track post-P6 external evidence reviewer checklist as local documentation only.",
        "- [x] State reviewer acceptance of real operator evidence is still missing.",
        "- [ ] Add operator-run PostgreSQL rehearsal evidence.",
        "- [ ] Record reviewer acceptance of real operator evidence.",
        "- [ ] Mark P3.4 rehearsal complete.",
    ):
        assert phrase in todo

    assert "- [x] Add operator-run PostgreSQL rehearsal evidence." not in todo
    assert "- [x] Record reviewer acceptance of real operator evidence." not in todo


def test_readiness_status_keeps_phase5_blocked_until_future_signoff() -> None:
    status = _text(STATUS)

    for phrase in (
        "reviewer acceptance of real operator-run evidence is not recorded.",
        "review checklist decision that accepts real operator evidence;",
        "Phase 5 should\nstart only after that signoff records accepted evidence.",
        "Every P3.4 artifact produced by the current toolchain must keep\n`ready_for_cutover=false`.",
    ):
        assert phrase in status


def test_readiness_closeout_doc_is_indexed_and_ci_wired() -> None:
    index = _text(INDEX)
    ci_yml = _text(CI_YML)
    verify_path = str(VERIFY_MD.relative_to(ROOT))

    assert verify_path in index
    assert "test_p3_4_external_evidence_readiness_closeout_contracts.py" in ci_yml
    assert verify_path in _text(VERIFY_MD)
