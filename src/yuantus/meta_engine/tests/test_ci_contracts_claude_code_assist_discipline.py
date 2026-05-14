from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
RUNBOOK = ROOT / "docs/RUNBOOK_CLAUDE_CODE_PARALLEL_WORKTREE.md"
DEV_MD = (
    ROOT
    / "docs/DEV_AND_VERIFICATION_CLAUDE_CODE_ASSIST_DISCIPLINE_20260514.md"
)
PLAN = ROOT / "docs/DEVELOPMENT_NEXT_CYCLE_TODO_PLAN_20260426.md"
DELIVERY_DOC_INDEX = ROOT / "docs/DELIVERY_DOC_INDEX.md"
CI_YML = ROOT / ".github/workflows/ci.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_claude_code_runbook_pins_read_only_default_and_advisory_scope() -> None:
    runbook = _text(RUNBOOK)

    for token in (
        "claude -p --no-session-persistence --tools \"\"",
        "Use read-only mode as the default",
        "Read-only Claude Code output is advisory.",
        "does not authorize implementation",
        "merge, phase transition, production cutover, or external evidence signoff",
        "Use worktree mode only after the user explicitly authorizes Claude Code to\nwrite code for a bounded task.",
        "Do not treat a Claude Code recommendation as a user opt-in to start a blocked\n  phase.",
        "Do not include secrets, webhook URLs, tokens, passwords, `.claude/`, or\n  `local-dev-env/`",
        "Do not bypass repository safety by using permission-skipping modes in the\n  shared worktree.",
    ):
        assert token in runbook


def test_claude_code_discipline_preserves_current_phase_gate() -> None:
    plan = _text(PLAN)
    runbook = _text(RUNBOOK)

    for token in (
        "Do not start Phase 5 provisioning or\n   production cutover until P3.4 evidence is accepted and recorded by signoff.",
        "If development continues before P3.4 evidence exists, it must be a new\n   trigger-gated taskbook outside this plan",
    ):
        assert token in plan

    assert "Phase gates still require explicit user authorization" in runbook
    assert "required\n  evidence artifacts" in runbook


def test_dev_verification_doc_records_no_runtime_or_phase_work() -> None:
    md = _text(DEV_MD)

    for token in (
        "Claude Code Assist Discipline",
        "No runtime code changes.",
        "No Phase 5 implementation.",
        "No P3.4 evidence synthesis or cutover enablement.",
        "Claude Code was used read-only",
        "repo-wide HTTPException scan: no offenders",
        "docs/DEV_AND_VERIFICATION_CLAUDE_CODE_ASSIST_DISCIPLINE_20260514.md",
    ):
        assert token in md


def test_claude_code_discipline_is_indexed_and_ci_wired() -> None:
    index = _text(DELIVERY_DOC_INDEX)
    ci_yml = _text(CI_YML)
    doc_path = str(DEV_MD.relative_to(ROOT))

    assert doc_path in index
    assert "test_ci_contracts_claude_code_assist_discipline.py" in ci_yml
