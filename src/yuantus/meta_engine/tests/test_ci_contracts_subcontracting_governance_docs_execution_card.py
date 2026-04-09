from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def test_subcontracting_governance_docs_execution_card_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    card = (
        repo_root
        / "docs"
        / "SUBCONTRACTING_GOVERNANCE_DOCS_SPLIT_EXECUTION_CARD_20260409.md"
    )
    residual = repo_root / "docs" / "DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md"
    coverage = repo_root / "docs" / "DIRTY_TREE_DOMAIN_COVERAGE_20260409.md"

    assert card.is_file(), f"Missing execution card: {card}"
    assert residual.is_file(), f"Missing residual note: {residual}"
    assert coverage.is_file(), f"Missing coverage note: {coverage}"

    card_text = card.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Subcontracting-Governance-Docs Split Execution Card",
        "docs/subcontracting-governance-pack",
        "docs(subcontracting): split governance and operator pack",
        "DEV_AND_VERIFICATION_SUBCONTRACTING_LAUNCH_CHECKLIST_SIGNOFF_PACK_20260403.md",
        "DEV_AND_VERIFICATION_SUBCONTRACTING_OPERATOR_RUNBOOK_DAILY_REVIEW_PLAYBOOK_20260403.md",
        "GOVERNANCE_CONTRACT_SURPASS_READING_GUIDE_20260331.md",
        "git diff --cached --stat",
        "keep this split doc-only",
    ):
        assert token in card_text, f"execution card missing token: {token}"

    residual_text = residual.read_text(encoding="utf-8", errors="replace")
    assert "SUBCONTRACTING_GOVERNANCE_DOCS_SPLIT_EXECUTION_CARD_20260409.md" in residual_text

    coverage_text = coverage.read_text(encoding="utf-8", errors="replace")
    assert "subcontracting-governance-docs" in coverage_text
