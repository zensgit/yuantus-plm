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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_verify_all_supports_reusing_healthy_existing_stack() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    text = _read(verify_all)

    assert "first_healthy_dedup_base_url()" in text, (
        "verify_all.sh should provide a helper to probe healthy Dedup endpoints."
    )
    assert "can_reuse_running_stack()" in text, (
        "verify_all.sh should support reusing an already-healthy stack when START_DEDUP_STACK=1."
    )
    assert "if can_reuse_running_stack; then" in text, (
        "verify_all.sh should check for reusable healthy stack before docker compose startup."
    )
    assert "detected healthy existing stack; reusing current services" in text, (
        "verify_all.sh should log explicit reuse mode for operator visibility."
    )
    assert "export YUANTUS_DEDUP_VISION_BASE_URL=\"$REUSED_DEDUP_BASE_URL\"" in text, (
        "verify_all.sh should propagate reused Dedup endpoint into child verification scripts."
    )
    assert "label=com.docker.compose.service=worker" in text, (
        "verify_all.sh should inspect compose worker container status for docker-worker mode warnings."
    )

