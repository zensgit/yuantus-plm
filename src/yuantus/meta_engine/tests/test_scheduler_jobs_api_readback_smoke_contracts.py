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


def test_scheduler_jobs_api_readback_smoke_script_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_scheduler_jobs_api_readback_smoke.sh"

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
        "local-dev only",
        "GET /api/v1/jobs/{job_id}",
        "run_scheduler_audit_retention_activation_smoke.sh",
        "job_readback.json",
        "shared-dev",
        "production",
    ):
        assert token in help_text

    text = script.read_text(encoding="utf-8")
    for token in (
        'if [[ "${db_url}" != sqlite:///* ]]',
        'local_data_dir="${repo_root}/local-dev-env/data"',
        "Refusing DB outside local-dev-env/data",
        "/api/v1/auth/login",
        "/api/v1/jobs/${job_id}",
        "authorization: Bearer",
        "expected completed status",
        "payload.result.deleted=2",
        "not for shared-dev or production",
    ):
        assert token in text


def test_scheduler_jobs_api_readback_doc_and_script_indexes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    doc = (
        repo_root
        / "docs"
        / "DEV_AND_VERIFICATION_SCHEDULER_JOBS_API_READBACK_SMOKE_20260421.md"
    )
    delivery_doc_index = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    delivery_scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert doc.is_file(), f"Missing doc: {doc}"
    assert doc.name in delivery_doc_index.read_text(encoding="utf-8")

    scripts_index_text = delivery_scripts_index.read_text(encoding="utf-8")
    assert "run_scheduler_jobs_api_readback_smoke.sh" in scripts_index_text

    doc_text = doc.read_text(encoding="utf-8")
    for token in (
        "scripts/run_scheduler_jobs_api_readback_smoke.sh",
        "GET /api/v1/jobs/{job_id}",
        "job_readback.json",
        "audit_retention_prune",
        "local-dev only",
    ):
        assert token in doc_text
