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


def test_verify_all_health_http_code_is_normalized_to_three_digits() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    text = _read(verify_all)

    assert "api_health_http_code()" in text, (
        "verify_all.sh should provide a dedicated helper for API health HTTP code probing."
    )
    assert "[[ ! \"$http_code\" =~ ^[0-9]{3}$ ]]" in text, (
        "verify_all.sh should normalize curl output to a strict 3-digit HTTP code."
    )
    assert 'HTTP_CODE="$(api_health_http_code)"' in text, (
        "verify_all.sh should use api_health_http_code() in preflight retry loop."
    )
    assert '|| echo "000"' not in text, (
        "verify_all.sh should avoid inline `|| echo \"000\"` fallback because it can produce "
        "duplicated values like `000000`."
    )
