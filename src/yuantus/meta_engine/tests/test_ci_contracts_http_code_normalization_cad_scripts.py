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


def test_cad_scripts_normalize_http_codes_and_avoid_echo_fallback() -> None:
    repo_root = _find_repo_root(Path(__file__))
    scripts = [
        repo_root / "scripts" / "verify_cad_preview_2d.sh",
        repo_root / "scripts" / "verify_cad_ocr_titleblock.sh",
        repo_root / "scripts" / "verify_docdoku_alignment.sh",
        repo_root / "scripts" / "verify_cad_real_samples.sh",
    ]

    for script in scripts:
        assert script.is_file(), f"Missing script: {script}"
        text = _read(script)
        assert "normalize_http_code()" in text, (
            f"{script} should define normalize_http_code() for robust curl code handling."
        )
        assert '[0-9]{3}' in text, (
            f"{script} should normalize HTTP status codes to strict 3-digit values."
        )
        assert '|| echo "000"' not in text, (
            f"{script} should not use inline `|| echo \"000\"` fallback (can produce 000000)."
        )

