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


def test_p2_observation_regression_workflow_contracts() -> None:
    repo_root = _find_repo_root(Path(__file__))
    wf = repo_root / ".github" / "workflows" / "p2-observation-regression.yml"
    assert wf.is_file(), f"Missing workflow: {wf}"
    wf_text = _read(wf)

    for token in (
        "name: p2-observation-regression",
        "workflow_dispatch:",
        "permissions:",
        "contents: read",
        "actions: read",
        "concurrency:",
        "cancel-in-progress: true",
        "github.ref",
        "timeout-minutes: 30",
    ):
        assert token in wf_text, f"workflow missing token: {token}"

    for token in (
        "base_url:",
        "tenant_id:",
        "org_id:",
        "username:",
        "environment:",
        "company_id:",
        "eco_type:",
        "eco_state:",
        "deadline_from:",
        "deadline_to:",
        'default: "tenant-1"',
        'default: "org-1"',
        'default: "admin"',
        'default: "workflow-dispatch"',
    ):
        assert token in wf_text, f"workflow missing dispatch input token: {token}"

    for token in (
        "Validate auth configuration",
        "secrets.P2_OBSERVATION_TOKEN",
        "secrets.P2_OBSERVATION_PASSWORD",
        "provide secrets.P2_OBSERVATION_TOKEN or secrets.P2_OBSERVATION_PASSWORD",
        "Run P2 observation regression",
        "bash scripts/run_p2_observation_regression.sh",
        "EVAL_MODE: current-only",
        "OUTPUT_DIR: tmp/p2-observation-workflow/${{ github.run_id }}",
        "Write observation summary to job summary",
        'echo "## P2 Observation Regression" >> "$GITHUB_STEP_SUMMARY"',
        'cat "${OUTPUT_DIR}/OBSERVATION_RESULT.md" >> "$GITHUB_STEP_SUMMARY"',
        'cat "${OUTPUT_DIR}/OBSERVATION_EVAL.md" >> "$GITHUB_STEP_SUMMARY"',
        "Upload P2 observation regression evidence",
        "if: always()",
        "name: p2-observation-regression",
        "path: tmp/p2-observation-workflow/${{ github.run_id }}",
        "if-no-files-found: error",
        "retention-days: 14",
    ):
        assert token in wf_text, f"workflow missing execution/artifact token: {token}"

    doc = repo_root / "docs" / "P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md"
    assert doc.is_file(), f"Missing doc: {doc}"
    doc_text = _read(doc)
    for token in (
        "gh workflow run p2-observation-regression",
        "P2_OBSERVATION_TOKEN",
        "P2_OBSERVATION_PASSWORD",
        "current-only",
        "p2-observation-regression",
    ):
        assert token in doc_text, f"workflow dispatch doc missing token: {token}"
