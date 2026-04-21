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


def test_scheduler_bom_to_mbom_activation_smoke_script_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_scheduler_bom_to_mbom_activation_smoke.sh"

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
        "refuses DB URLs outside ./local-dev-env/data/",
        "bom_to_mbom_sync",
        "shared-dev",
        "ManufacturingBOM",
        "--plant",
    ):
        assert token in help_text

    text = script.read_text(encoding="utf-8")
    for token in (
        'if [[ "${db_url}" != sqlite:///* ]]',
        'local_data_dir="${repo_root}/local-dev-env/data"',
        "Refusing DB outside local-dev-env/data",
        "YUANTUS_SCHEDULER_ECO_ESCALATION_ENABLED=false",
        "YUANTUS_SCHEDULER_AUDIT_RETENTION_ENABLED=false",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_ENABLED=true",
        "YUANTUS_SCHEDULER_BOM_TO_MBOM_SOURCE_ITEM_IDS=${root_item_id}",
        "scheduler:bom_to_mbom_sync:",
        "Delete generated MBOM lines before ManufacturingBOM rows",
        "existing_mbom_ids",
        "Delete the relationship item separately first",
        "for item_id in (relationship_id,):",
        "for item_id in (child_item_id, root_item_id):",
        "expected exactly one enqueued job",
        "expected worker result created=1",
        "missing MBOM line traceability to EBOM relationship",
    ):
        assert token in text


def test_scheduler_bom_to_mbom_activation_doc_is_indexed() -> None:
    repo_root = _find_repo_root(Path(__file__))
    doc = (
        repo_root
        / "docs"
        / "DEV_AND_VERIFICATION_SCHEDULER_BOM_TO_MBOM_ACTIVATION_RUNBOOK_20260421.md"
    )
    index = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    scripts_index = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"

    assert doc.is_file(), f"Missing doc: {doc}"
    index_text = index.read_text(encoding="utf-8")
    assert doc.name in index_text
    scripts_index_text = scripts_index.read_text(encoding="utf-8")
    assert "run_scheduler_bom_to_mbom_activation_smoke.sh" in scripts_index_text

    doc_text = doc.read_text(encoding="utf-8")
    for token in (
        "scripts/run_scheduler_bom_to_mbom_activation_smoke.sh",
        "shared-dev 142 remains default-off",
        "bom_to_mbom_sync",
        "ManufacturingBOM",
        "MBOMLine",
        "scheduler -> meta_conversion_jobs -> worker",
    ):
        assert token in doc_text
