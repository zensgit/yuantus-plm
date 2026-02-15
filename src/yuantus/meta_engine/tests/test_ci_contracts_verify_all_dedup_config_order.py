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


def test_verify_all_prints_dedup_config_after_port_resolution() -> None:
    repo_root = _find_repo_root(Path(__file__))
    verify_all = repo_root / "scripts" / "verify_all.sh"
    assert verify_all.is_file(), f"Missing {verify_all}"
    lines = _read(verify_all).splitlines()

    resolve_line = -1
    invoke_line = -1
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if resolve_line < 0 and 'echo "Dedup port resolved:' in stripped:
            resolve_line = idx
        if invoke_line < 0 and stripped == "print_dedup_config":
            invoke_line = idx
            break

    assert resolve_line > 0, "verify_all.sh should log resolved Dedup ports."
    assert invoke_line > 0, "verify_all.sh should invoke print_dedup_config in preflight."
    assert invoke_line > resolve_line, (
        "verify_all.sh should print DEDUP_CONFIG after Dedup port resolution so effective "
        "values reflect runtime-resolved ports."
    )

