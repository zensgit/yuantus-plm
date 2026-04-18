from __future__ import annotations

import subprocess
import sys
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


def _bash_n(script: Path) -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(script)],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def _py_compile(script: Path) -> None:
    cp = subprocess.run(  # noqa: S603,S607
        [sys.executable, "-m", "py_compile", str(script)],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr


def test_p2_observation_regression_scripts_are_syntax_valid() -> None:
    repo_root = _find_repo_root(Path(__file__))
    wrapper = repo_root / "scripts" / "run_p2_observation_regression.sh"
    evaluator = repo_root / "scripts" / "evaluate_p2_observation_results.py"

    assert wrapper.is_file(), f"Missing wrapper script: {wrapper}"
    assert evaluator.is_file(), f"Missing evaluator script: {evaluator}"

    _bash_n(wrapper)
    _py_compile(evaluator)


def test_p2_observation_regression_wrapper_help_exposes_eval_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    wrapper = repo_root / "scripts" / "run_p2_observation_regression.sh"
    assert wrapper.is_file(), f"Missing wrapper script: {wrapper}"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(wrapper), "--help"],
        text=True,
        capture_output=True,
        cwd=repo_root,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""

    assert "scripts/run_p2_observation_regression.sh" in out
    assert "EVAL_MODE" in out
    assert "EXPECT_DELTAS" in out
    assert "EVAL_OUTPUT" in out
    assert "OBSERVATION_EVAL.md" in out


def test_p2_observation_regression_docs_keep_evaluator_entrypoints_linked() -> None:
    repo_root = _find_repo_root(Path(__file__))

    docs_with_tokens = {
        repo_root / "docs" / "P2_OBSERVATION_REGRESSION_EVALUATION.md": [
            "scripts/evaluate_p2_observation_results.py",
            "state-change",
            "--expect-delta",
        ],
        repo_root / "docs" / "P2_OBSERVATION_REGRESSION_ONE_COMMAND.md": [
            "scripts/run_p2_observation_regression.sh",
            'EVAL_MODE="readonly"',
            "OBSERVATION_DIFF.md",
        ],
        repo_root / "docs" / "P2_OBSERVATION_REGRESSION_TRIGGER_CHECKLIST.md": [
            "scripts/run_p2_observation_regression.sh",
            "scripts/evaluate_p2_observation_results.py",
            "OBSERVATION_EVAL.md",
        ],
        repo_root / "docs" / "P2_ONE_PAGE_DEV_GUIDE.md": [
            "scripts/run_p2_observation_regression.sh",
            "scripts/evaluate_p2_observation_results.py",
            "OBSERVATION_EVAL.md",
        ],
        repo_root / "docs" / "P2_REMOTE_OBSERVATION_REGRESSION_RUNBOOK.md": [
            "scripts/evaluate_p2_observation_results.py",
            "OBSERVATION_RESULT.md",
            "readonly",
        ],
    }

    for path, tokens in docs_with_tokens.items():
        assert path.is_file(), f"Missing doc: {path}"
        text = _read(path)
        for token in tokens:
            assert token in text, f"{path} is missing token: {token}"


def test_delivery_doc_index_tracks_p2_observation_evaluator_docs() -> None:
    repo_root = _find_repo_root(Path(__file__))
    index_path = repo_root / "docs" / "DELIVERY_DOC_INDEX.md"
    text = _read(index_path)

    required_entries = [
        "docs/P2_OBSERVATION_REGRESSION_EVALUATION.md",
        "docs/DEV_AND_VERIFICATION_P2_OBSERVATION_REGRESSION_EVALUATION_20260418.md",
        "docs/DEV_AND_VERIFICATION_P2_OBSERVATION_REGRESSION_EVALUATOR_CI_CONTRACT_20260418.md",
    ]

    for entry in required_entries:
        assert entry in text, f"DELIVERY_DOC_INDEX.md missing entry: {entry}"
