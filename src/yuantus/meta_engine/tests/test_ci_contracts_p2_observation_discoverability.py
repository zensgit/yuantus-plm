from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "docs").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + docs/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_p2_observation_docs_are_discoverable_from_readme_runbooks() -> None:
    repo_root = _find_repo_root(Path(__file__))
    readme = repo_root / "README.md"
    assert readme.is_file(), f"Missing {readme}"

    text = _read(readme)
    for token in (
        "docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md",
        "docs/P2_ONE_PAGE_DEV_GUIDE.md",
        "docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md",
    ):
        assert token in text, f"README.md missing P2 observation runbook token: {token}"


def test_p2_observation_scripts_are_discoverable_from_delivery_scripts_index() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    assert index_path.is_file(), f"Missing {index_path}"

    text = _read(index_path)
    for token in (
        "verify_p2_dev_observation_startup.sh",
        "run_p2_observation_regression.sh",
        "run_p2_observation_regression_workflow.sh",
        "render_p2_observation_result.py",
        "compare_p2_observation_results.py",
        "evaluate_p2_observation_results.py",
        "`run_p2_observation_regression.sh` is the canonical local/shared-dev wrapper",
        "`run_p2_observation_regression_workflow.sh` is the canonical local wrapper",
        "`print_p2_shared_dev_observation_commands.sh` prints the canonical P2 shared-dev shell and workflow entry commands.",
    ):
        assert token in text, f"DELIVERY_SCRIPTS_INDEX missing P2 observation token: {token}"


def test_p2_observation_handoff_and_runbooks_are_indexed_in_delivery_doc_index() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    assert index_path.is_file(), f"Missing {index_path}"

    text = _read(index_path)
    for token in (
        "docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md",
        "docs/P2_ONE_PAGE_DEV_GUIDE.md",
        "docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md",
        "docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md",
        "docs/DEV_AND_VERIFICATION_P2_OBSERVATION_WORKFLOW_WRAPPER_20260418.md",
    ):
        assert token in text, f"DELIVERY_DOC_INDEX missing P2 observation doc token: {token}"


def test_p2_remote_observation_runbook_stays_on_wrapper_path_for_baseline_and_rerun() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runbook_path = repo_root / "docs" / "P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md"
    assert runbook_path.is_file(), f"Missing {runbook_path}"

    text = _read(runbook_path)
    for token in (
        "bash scripts/run_p2_observation_regression.sh",
        'TOKEN="$ADMIN_TOKEN"',
        'ADMIN_TOKEN=$(',
        'Authorization: Bearer $ADMIN_TOKEN',
    ):
        assert token in text, f"P2 remote observation runbook missing token: {token}"
