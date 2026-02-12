from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + src/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_dedup_review_can_auto_trigger_workflow() -> None:
    repo_root = _find_repo_root(Path(__file__))
    service_py = repo_root / "src" / "yuantus" / "meta_engine" / "dedup" / "service.py"
    text = _read(service_py)

    assert "rule.auto_trigger_workflow" in text, (
        "DedupService.review_record must check rule.auto_trigger_workflow to start workflows."
    )
    assert "rule.workflow_map_id" in text, (
        "DedupService.review_record must use rule.workflow_map_id when starting workflows."
    )
    assert "_start_workflow_for_item" in text, (
        "DedupService should route workflow triggering via a helper to keep review_record readable."
    )
    assert "workflow_map_id required when auto_trigger_workflow=true" in text, (
        "Dedup rule creation/update must reject auto_trigger_workflow=true without workflow_map_id."
    )
