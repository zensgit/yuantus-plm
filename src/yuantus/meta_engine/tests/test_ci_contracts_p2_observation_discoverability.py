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
        "docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md",
        "docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md",
        "docs/P2_ONE_PAGE_DEV_GUIDE.md",
        "docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md",
        "docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md",
        "docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md",
    ):
        assert token in text, f"README.md missing P2 observation runbook token: {token}"


def test_p2_shared_dev_142_entrypoint_is_discoverable_from_readme_top_level_shared_dev_section() -> None:
    repo_root = _find_repo_root(Path(__file__))
    readme = repo_root / "README.md"
    assert readme.is_file(), f"Missing {readme}"

    text = _read(readme)
    for token in (
        "docs/P2_ONE_PAGE_DEV_GUIDE.md",
        "docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md",
        "bash scripts/run_p2_shared_dev_142_entrypoint.sh --help",
        "bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode print-readonly-commands",
        "bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode readonly-rerun",
        "bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-probe",
        "bash scripts/run_p2_shared_dev_142_entrypoint.sh --mode workflow-readonly-check",
    ):
        assert token in text, f"README.md missing shared-dev 142 selector token: {token}"


def test_p2_observation_scripts_are_discoverable_from_delivery_scripts_index() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_SCRIPTS_INDEX_20260202.md"
    assert index_path.is_file(), f"Missing {index_path}"

    text = _read(index_path)
    for token in (
        "print_p2_shared_dev_bootstrap_commands.sh",
        "print_p2_shared_dev_142_readonly_rerun_commands.sh",
        "print_p2_shared_dev_first_run_commands.sh",
        "print_p2_shared_dev_mode_selection.sh",
        "run_p2_shared_dev_142_entrypoint.sh",
        "run_p2_shared_dev_142_readonly_rerun.sh",
        "run_p2_shared_dev_142_workflow_probe.sh",
        "run_p2_shared_dev_142_workflow_readonly_check.sh",
        "precheck_p2_observation_regression.sh",
        "verify_p2_dev_observation_startup.sh",
        "run_p2_observation_regression.sh",
        "run_p2_observation_regression_workflow.sh",
        "render_p2_observation_result.py",
        "compare_p2_observation_results.py",
        "evaluate_p2_observation_results.py",
        "`print_p2_shared_dev_bootstrap_commands.sh` prints the server-side shared-dev bootstrap and post-bootstrap observation handoff commands.",
        "`print_p2_shared_dev_142_readonly_rerun_commands.sh` prints the fixed readonly rerun commands for the current official shared-dev 142 baseline, including the canonical `BASELINE_DIR`.",
        "`print_p2_shared_dev_first_run_commands.sh` prints the fixed first-run checklist for fresh or explicitly resettable shared-dev environments.",
        "`print_p2_shared_dev_mode_selection.sh` prints the decision gate between existing shared-dev rerun and first-run bootstrap, defaulting unknown environments to rerun.",
        "`run_p2_shared_dev_142_entrypoint.sh` is the single mode selector for shared-dev host `142.171.239.56`, routing to readonly-rerun, workflow-probe, workflow-readonly-check, or the expanded readonly command printout.",
        "`run_p2_shared_dev_142_readonly_rerun.sh` runs the current official shared-dev 142 readonly rerun end-to-end with fixed baseline defaults, optional baseline restore, precheck, and readonly evaluation.",
        "`run_p2_shared_dev_142_workflow_probe.sh` runs the fixed GitHub workflow-dispatch current-only probe for shared-dev host `142.171.239.56` and downloads the resulting artifact locally.",
        "`run_p2_shared_dev_142_workflow_readonly_check.sh` runs the fixed shared-dev 142 workflow probe, then locally compares the downloaded artifact against the official frozen readonly baseline and writes readonly diff/eval outputs.",
        "`precheck_p2_observation_regression.sh` is the cheap local shared-dev readiness probe",
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
        "docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md",
        "docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md",
        "docs/P2_ONE_PAGE_DEV_GUIDE.md",
        "docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md",
        "docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md",
        "docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md",
        "docs/DEV_AND_VERIFICATION_P2_OBSERVATION_WORKFLOW_WRAPPER_20260418.md",
    ):
        assert token in text, f"DELIVERY_DOC_INDEX missing P2 observation doc token: {token}"


def test_dev_and_verification_p2_readme_runbook_alignment_doc_tracks_promoted_p2_operator_docs() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "docs" / "DEV_AND_VERIFICATION_P2_README_RUNBOOK_DISCOVERABILITY_ALIGNMENT_20260420.md"
    assert path.is_file(), f"Missing P2 README runbook alignment dev doc: {path}"

    text = _read(path)
    for token in (
        "README.md",
        "docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md",
        "docs/P2_OBSERVATION_REGRESSION_WORKFLOW_DISPATCH.md",
        "docs/P2_ONE_PAGE_DEV_GUIDE.md",
        "docs/P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md",
        "docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md",
    ):
        assert token in text, f"P2 README runbook alignment dev doc missing token: {token}"


def test_dev_and_verification_p2_readme_first_run_checklist_doc_tracks_first_run_entrypoint() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "docs" / "DEV_AND_VERIFICATION_P2_README_FIRST_RUN_CHECKLIST_DISCOVERABILITY_20260420.md"
    assert path.is_file(), f"Missing P2 first-run discoverability dev doc: {path}"

    text = _read(path)
    for token in (
        "README.md",
        "docs/P2_SHARED_DEV_FIRST_RUN_CHECKLIST.md",
        "docs/P2_OBSERVATION_REGRESSION_ONE_COMMAND.md",
        "docs/P2_SHARED_DEV_OBSERVATION_HANDOFF.md",
    ):
        assert token in text, f"P2 first-run discoverability dev doc missing token: {token}"


def test_p2_remote_observation_runbook_stays_on_wrapper_path_for_baseline_and_rerun() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runbook_path = repo_root / "docs" / "P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md"
    assert runbook_path.is_file(), f"Missing {runbook_path}"

    text = _read(runbook_path)
    for token in (
        "scripts/precheck_p2_observation_regression.sh",
        "bash scripts/run_p2_observation_regression.sh",
        "scripts/run_p2_shared_dev_142_entrypoint.sh",
        "print-readonly-commands",
        "readonly-rerun",
        "workflow-probe",
        "workflow-readonly-check",
        'TOKEN="$ADMIN_TOKEN"',
        'ADMIN_TOKEN=$(',
        'Authorization: Bearer $ADMIN_TOKEN',
    ):
        assert token in text, f"P2 remote observation runbook missing token: {token}"


def _extract_env_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if "<<'ENVEOF'" in line or '<<"ENVEOF"' in line or "<<ENVEOF" in line:
            current = []
            continue
        if current is not None and line.strip() == "ENVEOF":
            blocks.append("\n".join(current))
            current = None
            continue
        if current is not None:
            current.append(line)
    return blocks


def test_p2_shared_dev_env_file_examples_stay_repo_safe_and_precheck_compatible() -> None:
    repo_root = _find_repo_root(Path(__file__))
    targets = (
        repo_root / "docs" / "P2_SHARED_DEV_OBSERVATION_HANDOFF.md",
        repo_root / "docs" / "P2_ONE_PAGE_DEV_GUIDE.md",
        repo_root / "docs" / "P2_OBSERVATION_REGRESSION_ONE_COMMAND.md",
        repo_root / "docs" / "DEV_AND_VERIFICATION_P2_OBSERVATION_SHARED_DEV_EXECUTION_GATE_20260419.md",
        repo_root / "scripts" / "print_p2_shared_dev_observation_commands.sh",
    )

    for path in targets:
        text = _read(path)
        assert "$HOME/.config/yuantus/" in text, f"{path} should keep shared-dev env files outside the repo"
        assert "./p2-shared-dev.env" not in text, f"{path} should not point shared-dev credentials at repo root"
        assert "./p2-observation.env" not in text, f"{path} should not point observation credentials at repo root"
        assert "ARCHIVE_RESULT=1" in text, f"{path} should still document archive enablement"
        for block in _extract_env_blocks(text):
            assert "ARCHIVE_RESULT=1" not in block, f"{path} env-file example must stay precheck-compatible"


def test_p2_shared_dev_mode_selection_script_is_present() -> None:
    repo_root = _find_repo_root(Path(__file__))
    for path in (
        repo_root / "scripts" / "print_p2_shared_dev_bootstrap_commands.sh",
        repo_root / "scripts" / "print_p2_shared_dev_142_readonly_rerun_commands.sh",
        repo_root / "scripts" / "print_p2_shared_dev_first_run_commands.sh",
        repo_root / "scripts" / "print_p2_shared_dev_mode_selection.sh",
        repo_root / "scripts" / "print_p2_shared_dev_observation_commands.sh",
        repo_root / "scripts" / "run_p2_shared_dev_142_entrypoint.sh",
        repo_root / "scripts" / "run_p2_shared_dev_142_readonly_rerun.sh",
        repo_root / "scripts" / "run_p2_shared_dev_142_workflow_probe.sh",
        repo_root / "scripts" / "run_p2_shared_dev_142_workflow_readonly_check.sh",
    ):
        assert path.is_file(), f"Missing shared-dev observation script: {path}"


def test_p2_shared_dev_142_readonly_helper_tracks_current_official_baseline() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "scripts" / "print_p2_shared_dev_142_readonly_rerun_commands.sh"
    assert path.is_file(), f"Missing shared-dev 142 readonly helper: {path}"

    text = _read(path)
    for token in (
        "./tmp/p2-shared-dev-observation-20260419-193242",
        "./tmp/p2-shared-dev-observation-20260419-193242.tar.gz",
        'BASELINE_LABEL="shared-dev-142-readonly-20260419"',
        'EVAL_MODE="readonly"',
        "`142.171.239.56`",
    ):
        assert token in text, f"shared-dev 142 readonly helper missing token: {token}"


def test_p2_shared_dev_142_readonly_runner_tracks_current_official_baseline() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "scripts" / "run_p2_shared_dev_142_readonly_rerun.sh"
    assert path.is_file(), f"Missing shared-dev 142 readonly runner: {path}"

    text = _read(path)
    for token in (
        "$HOME/.config/yuantus/p2-shared-dev.env",
        "./tmp/p2-shared-dev-observation-20260419-193242",
        "./tmp/p2-shared-dev-observation-20260419-193242.tar.gz",
        "shared-dev-142-readonly-20260419",
        "shared-dev-142-readonly-precheck",
        "shared-dev-142-readonly",
        "scripts/validate_p2_shared_dev_env.sh",
        "scripts/precheck_p2_observation_regression.sh",
        "scripts/run_p2_observation_regression.sh",
    ):
        assert token in text, f"shared-dev 142 readonly runner missing token: {token}"


def test_p2_shared_dev_142_entrypoint_wrapper_exposes_all_modes() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "scripts" / "run_p2_shared_dev_142_entrypoint.sh"
    assert path.is_file(), f"Missing shared-dev 142 entrypoint wrapper: {path}"

    text = _read(path)
    for token in (
        "readonly-rerun",
        "workflow-probe",
        "workflow-readonly-check",
        "print-readonly-commands",
        "--dry-run",
        "scripts/run_p2_shared_dev_142_readonly_rerun.sh",
        "scripts/run_p2_shared_dev_142_workflow_probe.sh",
        "scripts/run_p2_shared_dev_142_workflow_readonly_check.sh",
        "scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh",
    ):
        assert token in text, f"shared-dev 142 entrypoint wrapper missing token: {token}"


def test_dev_and_verification_shared_dev_142_entrypoint_selector_doc_keeps_all_modes_visible() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "docs" / "DEV_AND_VERIFICATION_SHARED_DEV_142_ENTRYPOINT_SELECTOR_20260420.md"
    assert path.is_file(), f"Missing shared-dev 142 selector dev doc: {path}"

    text = _read(path)
    for token in (
        "scripts/run_p2_shared_dev_142_entrypoint.sh",
        "readonly-rerun",
        "workflow-probe",
        "workflow-readonly-check",
        "print-readonly-commands",
        "--dry-run",
    ):
        assert token in text, f"shared-dev 142 selector dev doc missing token: {token}"


def test_p2_shared_dev_142_workflow_probe_tracks_fixed_host_defaults() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "scripts" / "run_p2_shared_dev_142_workflow_probe.sh"
    assert path.is_file(), f"Missing shared-dev 142 workflow probe wrapper: {path}"

    text = _read(path)
    for token in (
        "http://142.171.239.56:7910",
        "tenant-1",
        "org-1",
        "shared-dev-142-workflow-probe",
        "current-only workflow probe",
        "scripts/run_p2_observation_regression_workflow.sh",
    ):
        assert token in text, f"shared-dev 142 workflow probe wrapper missing token: {token}"


def test_p2_shared_dev_142_workflow_readonly_check_wrapper_tracks_fixed_baseline() -> None:
    repo_root = _find_repo_root(Path(__file__))
    path = repo_root / "scripts" / "run_p2_shared_dev_142_workflow_readonly_check.sh"
    assert path.is_file(), f"Missing shared-dev 142 workflow readonly check wrapper: {path}"

    text = _read(path)
    for token in (
        "./tmp/p2-shared-dev-observation-20260419-193242",
        "./tmp/p2-shared-dev-observation-20260419-193242.tar.gz",
        "shared-dev-142-readonly-20260419",
        "workflow-probe-current",
        "WORKFLOW_READONLY_DIFF.md",
        "WORKFLOW_READONLY_EVAL.md",
        "WORKFLOW_READONLY_CHECK.md",
        "scripts/run_p2_shared_dev_142_workflow_probe.sh",
        "scripts/compare_p2_observation_results.py",
        "scripts/evaluate_p2_observation_results.py",
    ):
        assert token in text, f"shared-dev 142 workflow readonly check wrapper missing token: {token}"
