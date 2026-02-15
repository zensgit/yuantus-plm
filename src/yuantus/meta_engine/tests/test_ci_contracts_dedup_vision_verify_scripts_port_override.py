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


def test_verify_scripts_use_dedup_vision_port_in_default_base_url() -> None:
    repo_root = _find_repo_root(Path(__file__))
    scripts = [
        repo_root / "scripts" / "verify_cad_dedup_vision_s3.sh",
        repo_root / "scripts" / "verify_cad_dedup_relationship_s3.sh",
    ]
    for script in scripts:
        assert script.is_file(), f"Missing script: {script}"
        text = _read(script)
        assert "DEDUP_BASE_URL=" in text, f"{script} should define DEDUP_BASE_URL"
        assert "YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL" in text, (
            f"{script} should allow YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL as secondary fallback."
        )
        assert "http://localhost:${DEDUP_VISION_PORT:-8100}" in text, (
            f"{script} should honor DEDUP_VISION_PORT in default DEDUP_BASE_URL."
        )
        assert (
            'DEDUP_BASE_URL="${DEDUP_BASE_URL:-${YUANTUS_DEDUP_VISION_BASE_URL:-${YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL:-http://localhost:${DEDUP_VISION_PORT:-8100}}}}"'
            in text
        ), (
            f"{script} should keep fallback precedence: DEDUP_BASE_URL > "
            "YUANTUS_DEDUP_VISION_BASE_URL > YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL > localhost:DEDUP_VISION_PORT."
        )
