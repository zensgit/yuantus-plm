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


def test_dedup_vision_client_supports_host_network_fallback_for_compose_dns_failures() -> None:
    repo_root = _find_repo_root(Path(__file__))
    client_py = repo_root / "src" / "yuantus" / "integrations" / "dedup_vision.py"
    text = _read(client_py)

    assert "_candidate_base_urls" in text, (
        "Dedup Vision client should compute candidate base URLs for retry/fallback."
    )
    assert "host.docker.internal" in text, (
        "Dedup Vision client should support host-network fallback when compose DNS name "
        "is not resolvable from worker container."
    )
    assert "YUANTUS_DEDUP_VISION_FALLBACK_BASE_URL" in text, (
        "Dedup Vision client should allow explicit fallback URL override for ops tuning."
    )
    assert "except httpx.RequestError" in text, (
        "Dedup Vision client should retry on request-level failures (e.g. DNS resolution errors)."
    )


def test_dedup_vision_host_fallback_is_scoped_and_configurable() -> None:
    repo_root = _find_repo_root(Path(__file__))
    client_py = repo_root / "src" / "yuantus" / "integrations" / "dedup_vision.py"
    text = _read(client_py)

    assert 'if host not in {"dedup-vision", "yuantus-dedup-vision"}' in text, (
        "Host-network fallback must stay scoped to compose Dedup hostnames only."
    )
    assert "YUANTUS_DEDUP_VISION_FALLBACK_PORT" in text, (
        "Dedup Vision client should allow explicit fallback port override."
    )
    assert "DEDUP_VISION_PORT" in text, (
        "Dedup Vision fallback should honor compose port override via DEDUP_VISION_PORT."
    )
