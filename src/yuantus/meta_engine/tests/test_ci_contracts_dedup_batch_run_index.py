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


def test_dedup_batch_run_supports_index_flag_and_passes_it_through() -> None:
    repo_root = _find_repo_root(Path(__file__))
    router_py = repo_root / "src" / "yuantus" / "meta_engine" / "web" / "dedup_router.py"
    service_py = repo_root / "src" / "yuantus" / "meta_engine" / "dedup" / "service.py"

    router_text = _read(router_py)
    assert "class DedupBatchRunRequest" in router_text
    assert "index: bool = False" in router_text, (
        "dedup batch run request must expose `index: bool = False` to allow "
        "backfill/index runs."
    )
    assert "index=request.index" in router_text, (
        "dedup batch run endpoint must pass index flag through to service.run_batch "
        "(expected exact snippet: 'index=request.index')."
    )

    service_text = _read(service_py)
    assert "def run_batch(" in service_text
    assert "index: bool = False" in service_text, (
        "DedupService.run_batch must accept index flag for job payload."
    )
    assert "\"index\": bool(index)" in service_text, (
        "DedupService.run_batch must include index flag in job payload "
        '(expected exact snippet: \'"index": bool(index)\').'
    )
