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


def test_shell_scripts_do_not_use_inline_echo_000_http_fallback() -> None:
    repo_root = _find_repo_root(Path(__file__))
    scripts_dir = repo_root / "scripts"
    assert scripts_dir.is_dir(), f"Missing scripts dir: {scripts_dir}"

    offenders: list[str] = []
    patterns = ['|| echo "000"', "|| echo '000'"]
    for path in sorted(scripts_dir.glob("*.sh")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern in text:
                offenders.append(f"{path}: contains `{pattern}`")
                break

    assert not offenders, (
        "Shell scripts should avoid inline `|| echo \"000\"` fallback because curl with "
        "`-w '%{http_code}'` can already emit `000`, resulting in confusing `000000` output.\n"
        + "\n".join(offenders)
    )

