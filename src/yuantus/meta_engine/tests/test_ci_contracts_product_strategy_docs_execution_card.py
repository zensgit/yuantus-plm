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


def test_product_strategy_docs_execution_card_exists_and_is_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))
    card = repo_root / "docs" / "PRODUCT_STRATEGY_DOCS_SPLIT_EXECUTION_CARD_20260409.md"
    residual = repo_root / "docs" / "DIRTY_TREE_RESIDUAL_CLUSTERS_20260409.md"
    coverage = repo_root / "docs" / "DIRTY_TREE_DOMAIN_COVERAGE_20260409.md"

    assert card.is_file(), f"Missing execution card: {card}"
    assert residual.is_file(), f"Missing residual note: {residual}"
    assert coverage.is_file(), f"Missing coverage note: {coverage}"

    card_text = card.read_text(encoding="utf-8", errors="replace")
    for token in (
        "Product-Strategy-Docs Split Execution Card",
        "docs/product-strategy-pack",
        "docs(product): split sku and workflow ownership pack",
        "docs/PRODUCT_SKU_MATRIX.md",
        "docs/WORKFLOW_OWNERSHIP_RULES.md",
        "git diff --cached --stat",
        "keep this split doc-only",
    ):
        assert token in card_text, f"execution card missing token: {token}"

    residual_text = residual.read_text(encoding="utf-8", errors="replace")
    assert "PRODUCT_STRATEGY_DOCS_SPLIT_EXECUTION_CARD_20260409.md" in residual_text

    coverage_text = coverage.read_text(encoding="utf-8", errors="replace")
    assert "product-strategy-docs" in coverage_text
