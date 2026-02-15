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


def test_verify_all_is_truthy_is_defined_before_first_use() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    lines = _read(verify_all).splitlines()

    define_line = -1
    first_use_line = -1
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if define_line < 0 and stripped.startswith("is_truthy()"):
            define_line = idx
            continue
        if first_use_line < 0 and "is_truthy " in stripped and not stripped.startswith("#"):
            first_use_line = idx
            break

    assert define_line > 0, "verify_all.sh must define is_truthy()."
    assert first_use_line > 0, "verify_all.sh should call is_truthy at least once."
    assert define_line < first_use_line, (
        "verify_all.sh must define is_truthy before its first invocation to avoid "
        "runtime `command not found` errors."
    )
