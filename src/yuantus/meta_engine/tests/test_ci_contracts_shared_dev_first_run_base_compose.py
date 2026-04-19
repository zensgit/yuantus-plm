from __future__ import annotations

import subprocess
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "docs").is_dir() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + docs/ + scripts/)")


def _run_script(repo_root: Path, relative_path: str) -> str:
    result = subprocess.run(
        ["bash", relative_path],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_first_run_print_scripts_pin_base_compose() -> None:
    repo_root = _find_repo_root(Path(__file__))

    first_run_output = _run_script(repo_root, "scripts/print_p2_shared_dev_first_run_commands.sh")
    bootstrap_output = _run_script(repo_root, "scripts/print_p2_shared_dev_bootstrap_commands.sh")

    required_lines = {
        "docker compose -f docker-compose.yml --env-file ./deployments/docker/shared-dev.bootstrap.env \\",
        "docker compose -f docker-compose.yml up -d api worker",
    }
    for line in required_lines:
        assert line in first_run_output, f"Missing base compose line in first-run print script output: {line}"
        assert line in bootstrap_output, f"Missing base compose line in bootstrap print script output: {line}"

    forbidden_lines = {
        "docker compose --env-file ./deployments/docker/shared-dev.bootstrap.env \\",
        "docker compose up -d api worker",
    }
    for line in forbidden_lines:
        assert line not in first_run_output, f"First-run print script still exposes implicit compose usage: {line}"
        assert line not in bootstrap_output, f"Bootstrap print script still exposes implicit compose usage: {line}"


def test_first_run_docs_and_readme_pin_base_compose() -> None:
    repo_root = _find_repo_root(Path(__file__))

    required_paths = [
        repo_root / "docs" / "P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md",
        repo_root / "docs" / "P2_SHARED_DEV_BOOTSTRAP_HANDOFF.md",
        repo_root / "README.md",
    ]
    required_tokens = [
        "docker compose -f docker-compose.yml --env-file ./deployments/docker/shared-dev.bootstrap.env",
        "docker compose -f docker-compose.yml up -d api worker",
        "docker-compose.override.yml",
    ]

    for path in required_paths:
        text = _read(path)
        for token in required_tokens:
            assert token in text, f"{path.relative_to(repo_root)} missing expected shared-dev base compose token: {token}"
