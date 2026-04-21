from __future__ import annotations

import subprocess
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "scripts").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root")


def test_scheduler_dry_run_preflight_script_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_scheduler_dry_run_preflight.sh"

    assert script.is_file(), f"Missing script: {script}"

    syntax = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(script)],
        text=True,
        capture_output=True,
    )
    assert syntax.returncode == 0, syntax.stdout + "\n" + syntax.stderr

    help_run = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )
    assert help_run.returncode == 0, help_run.stdout + "\n" + help_run.stderr
    help_text = help_run.stdout or ""
    for token in (
        "Usage:",
        "yuantus scheduler --once --dry-run",
        "validates dry-run did not enqueue jobs",
        "--allow-non-local-db",
        "--respect-enabled",
        "must not create rows in meta_conversion_jobs",
    ):
        assert token in help_text

    text = script.read_text(encoding="utf-8")
    for token in (
        "Refusing non-local DB URL without --allow-non-local-db",
        "Refusing SQLite DB outside local-dev-env/data",
        "--dry-run",
        "--force",
        "scheduler_dry_run.json",
        "job_counts.json",
        "validation.json",
        "dry-run unexpectedly enqueued jobs",
        "meta_conversion_jobs changed during dry-run",
    ):
        assert token in text


def test_scheduler_dry_run_preflight_doc_and_script_indexes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    doc = (
        repo_root
        / "docs"
        / "DEV_AND_VERIFICATION_SCHEDULER_DRY_RUN_PREFLIGHT_HELPER_20260421.md"
    )
    delivery_doc_index = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    delivery_scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert doc.is_file(), f"Missing doc: {doc}"
    assert doc.name in delivery_doc_index.read_text(encoding="utf-8")

    scripts_index_text = delivery_scripts_index.read_text(encoding="utf-8")
    assert "run_scheduler_dry_run_preflight.sh" in scripts_index_text

    doc_text = doc.read_text(encoding="utf-8")
    for token in (
        "scripts/run_scheduler_dry_run_preflight.sh",
        "job_count_before",
        "job_count_after",
        "would_enqueue",
        "shared-dev/prod DB targets require --allow-non-local-db",
    ):
        assert token in doc_text
