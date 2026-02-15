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


def test_verify_all_env_allowlist_includes_dedup_fallback_vars() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    text = _read(verify_all)

    assert "YUANTUS_DEDUP_VISION_BASE_URL" in text, (
        "verify_all.sh should preserve YUANTUS_DEDUP_VISION_BASE_URL from server env."
    )
    assert "DEDUP_VISION_PORT" in text, (
        "verify_all.sh should preserve DEDUP_VISION_PORT for non-default Dedup host port setups."
    )
    assert "YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL" in text, (
        "verify_all.sh should preserve YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL from server env."
    )
    assert "YUANTUS_DEDUP_VISION_FALLBACK_PORT" in text, (
        "verify_all.sh should preserve YUANTUS_DEDUP_VISION_FALLBACK_PORT from server env."
    )
