"""Contracts for the post-P6 next-cycle operating gate.

These tests prevent the planning docs from drifting back into an unsafe
"continue means start Phase 5" state. Phase 5 remains blocked until the
external P3.4 PostgreSQL rehearsal evidence exists and is accepted.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md"
POST_P6_REFRESH = (
    ROOT / "docs/DEV_AND_VERIFICATION_NEXT_CYCLE_POST_P6_STATUS_REFRESH_20260510.md"
)
POST_P6_GATE_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_NEXT_CYCLE_POST_P6_PLAN_GATE_CONTRACTS_20260511.md"
)
RUNBOOK = ROOT / "docs/RUNBOOK_TENANT_MIGRATIONS_20260427.md"
INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_plan_marks_phase4_and_phase6_complete_after_post_p6_closeout() -> None:
    plan = _text(PLAN)

    assert "**2026-05-10 status refresh**" in plan
    assert "Phase 4 search incremental/reports closed in #499" in plan
    assert "Phase 6 external\n> circuit breakers closed in #503" in plan
    assert "| S6 搜索/索引 | ✅ Done |" in plan
    assert "| Roadmap §11 可观测 | ✅ Done |" in plan
    assert "## 8. Phase 4 — Search Incremental + Reports (S6)" in plan
    assert "**Status as of `main=61b5951`**: complete." in plan
    assert "## 10. Phase 6 — External-Service Circuit Breakers" in plan


def test_phase5_is_explicitly_blocked_by_p3_4_external_evidence() -> None:
    plan = _text(PLAN)
    refresh = _text(POST_P6_REFRESH)

    required_phrases = (
        "Phase 5 tenant/org provisioning + backup/restore",
        "blocked\n> until P3.4 real non-production PostgreSQL rehearsal evidence is accepted",
        "**Status as of `main=61b5951`**: not started.",
        "Do not start P5.1 local implementation",
        "until real non-production PostgreSQL rehearsal evidence has been accepted",
        "Do not start Phase 5 provisioning or\n   production cutover until P3.4 evidence is accepted",
    )
    for phrase in required_phrases:
        assert phrase in plan

    assert "Do not treat \"continue\" after Phase 6 as permission to start Phase 5." in refresh
    assert "Phase 5 depends on the Phase 3 external evidence gate." in refresh
    assert "A repository-only Phase 5 implementation would create a provisioning surface" in refresh
    assert "No Phase 5 implementation." in refresh


def test_stale_phase4_next_candidate_language_does_not_reappear() -> None:
    plan = _text(PLAN)
    refresh = _text(POST_P6_REFRESH)

    forbidden = (
        "next candidate is Phase 4 P4.1",
        "Phase 4 (incremental + reports) remains the next internal-code candidate",
        "Phase 6 circuit breakers remain trigger-gated",
    )
    for phrase in forbidden:
        assert phrase not in plan
        assert phrase not in refresh


def test_p3_4_external_stop_gate_remains_six_part_and_real_evidence_only() -> None:
    runbook = _text(RUNBOOK)
    handoff = _text(
        ROOT / "docs/DEV_AND_VERIFICATION_PHASE3_TENANT_IMPORT_EXTERNAL_OPERATOR_HANDOFF_20260506.md"
    )

    for phrase in (
        "Do not start P3.4 cutover (data migration / runtime enablement) until all are true:",
        "A named pilot tenant exists.",
        "Non-production rehearsal DB is available.",
        "Backup/restore owner is named.",
        "Rehearsal window is scheduled.",
        "P3.3.1, P3.3.2, and P3.3.3 are merged and smoke green.",
        "Table classification artifact is signed off.",
    ):
        assert phrase in runbook

    for phrase in (
        "No additional local development should try to close P3.4 without real operator\nevidence.",
        "real non-production PostgreSQL\nsource/target databases",
        "Synthetic drill: true",
        "Real rehearsal evidence: false",
        "Ready for cutover: false",
        "Do not mark P3.4 rehearsal complete.",
    ):
        assert phrase in handoff


def test_post_p6_gate_doc_is_indexed_and_ci_runs_this_contract() -> None:
    index = _text(INDEX)
    ci_yml = _text(CI_YML)
    gate_doc = str(POST_P6_GATE_MD.relative_to(ROOT))

    assert gate_doc in index
    assert "test_next_cycle_post_p6_plan_gate_contracts.py" in ci_yml
    assert gate_doc in _text(POST_P6_GATE_MD)
