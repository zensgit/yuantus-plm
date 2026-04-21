from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_shared_dev_142_readonly_guard_workflow_contracts() -> None:
    repo_root = _find_repo_root(Path(__file__))

    workflow = repo_root / ".github" / "workflows" / "shared-dev-142-readonly-guard.yml"
    assert workflow.is_file(), f"Missing workflow: {workflow}"
    workflow_text = _read(workflow)

    for token in (
        "name: shared-dev-142-readonly-guard",
        "workflow_dispatch: {}",
        "schedule:",
        'cron: "20 18 * * *"',
        "permissions:",
        "contents: read",
        "actions: write",
        "concurrency:",
        "group: ${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress: true",
        "timeout-minutes: 45",
        "GH_TOKEN: ${{ github.token }}",
        "GITHUB_TOKEN: ${{ github.token }}",
        "OUTPUT_DIR: tmp/p2-shared-dev-142-readonly-guard/${{ github.run_id }}",
        "Run shared-dev 142 readonly guard",
        "id: run_shared_dev_142_readonly_guard",
        "bash scripts/run_p2_shared_dev_142_workflow_readonly_check.sh",
        '--output-dir "${OUTPUT_DIR}"',
        '--repo "${{ github.repository }}"',
        "--ref main",
        "Write readonly guard summary to job summary",
        "steps.run_shared_dev_142_readonly_guard.outcome",
        "WORKFLOW_DISPATCH_RESULT.md",
        "WORKFLOW_READONLY_CHECK.md",
        "WORKFLOW_READONLY_EVAL.md",
        "Upload readonly guard evidence",
        "name: shared-dev-142-readonly-guard",
        "tmp/p2-shared-dev-142-readonly-guard/${{ github.run_id }}",
        "tmp/p2-shared-dev-142-readonly-guard/${{ github.run_id }}.tar.gz",
        "retention-days: 14",
        "Fail workflow when readonly guard failed",
        "ERROR: shared-dev 142 readonly guard execution failed",
    ):
        assert token in workflow_text, f"workflow missing token: {token}"

    tracked_baseline_dir = (
        repo_root / "artifacts" / "p2-observation" / "shared-dev-142-readonly-20260421"
    )
    assert tracked_baseline_dir.is_dir(), (
        "Missing tracked readonly baseline dir for shared-dev 142: "
        f"{tracked_baseline_dir}"
    )
    for file_name in (
        "OBSERVATION_RESULT.md",
        "README.txt",
        "anomalies.json",
        "baseline_policy.json",
        "export.csv",
        "export.json",
        "items.json",
        "summary.json",
    ):
        assert (tracked_baseline_dir / file_name).is_file(), (
            "Tracked readonly baseline missing file: "
            f"{tracked_baseline_dir / file_name}"
        )

    for script_name in (
        "run_p2_shared_dev_142_readonly_rerun.sh",
        "run_p2_shared_dev_142_workflow_readonly_check.sh",
    ):
        script_text = _read(repo_root / "scripts" / script_name)
        for token in (
            'default_tracked_baseline_dir="./artifacts/p2-observation/shared-dev-142-readonly-20260421"',
            "Restored canonical baseline dir from tracked repo baseline:",
            "Missing baseline dir, archive, and tracked repo baseline:",
        ):
            assert token in script_text, f"{script_name} missing token: {token}"
