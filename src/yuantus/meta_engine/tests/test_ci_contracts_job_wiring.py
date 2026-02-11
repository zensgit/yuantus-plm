from __future__ import annotations

import re
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


def _extract_contract_check_test_paths(ci_workflow_text: str) -> set[str]:
    lines = ci_workflow_text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "- name: Contract checks (perf workflows + delivery doc index)":
            start = i
            break
    assert start is not None, "Missing CI contracts step: 'Contract checks (perf workflows + delivery doc index)'"

    end = len(lines)
    for j in range(start + 1, len(lines)):
        # End at the next top-level job key under `jobs:`.
        if re.match(r"^  [a-zA-Z0-9_-]+:\s*$", lines[j]):
            end = j
            break

    block = "\n".join(lines[start:end])
    return set(re.findall(r"src/yuantus/meta_engine/tests/test_[a-zA-Z0-9_]+\.py", block))


def test_ci_contracts_job_includes_all_contract_tests() -> None:
    repo_root = _find_repo_root(Path(__file__))

    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    assert ci_yml.is_file()
    configured = _extract_contract_check_test_paths(_read(ci_yml))

    tests_dir = repo_root / "src" / "yuantus" / "meta_engine" / "tests"
    contract_pattern_paths = sorted(
        p.relative_to(repo_root).as_posix() for p in tests_dir.glob("test_*contracts*.py")
    )
    assert contract_pattern_paths, "Expected at least one test_*contracts*.py file"

    # Contract-adjacent checks are intentionally explicit to avoid accidental
    # broadening if unrelated test names change.
    explicit_contract_checks = {
        "src/yuantus/meta_engine/tests/test_ci_shell_scripts_syntax.py",
        "src/yuantus/meta_engine/tests/test_perf_gate_config_file.py",
        "src/yuantus/meta_engine/tests/test_perf_ci_baseline_downloader_script.py",
        "src/yuantus/meta_engine/tests/test_readme_runbook_references.py",
        "src/yuantus/meta_engine/tests/test_readme_runbooks_are_indexed_in_delivery_doc_index.py",
        "src/yuantus/meta_engine/tests/test_runbook_index_completeness.py",
        "src/yuantus/meta_engine/tests/test_dev_and_verification_doc_index_completeness.py",
        "src/yuantus/meta_engine/tests/test_delivery_doc_index_references.py",
    }

    expected = set(contract_pattern_paths) | explicit_contract_checks
    missing = sorted(expected - configured)
    assert not missing, (
        "Contract checks missing from .github/workflows/ci.yml contracts step:\n"
        + "\n".join(f"- {p}" for p in missing)
    )

    stale = sorted(p for p in configured if p.startswith("src/yuantus/meta_engine/tests/") and not (repo_root / p).is_file())
    assert not stale, (
        "CI contracts step references test files that do not exist:\n"
        + "\n".join(f"- {p}" for p in stale)
    )

