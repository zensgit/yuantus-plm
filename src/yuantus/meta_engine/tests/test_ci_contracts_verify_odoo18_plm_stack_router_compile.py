from __future__ import annotations

import re
import subprocess
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


def _script_text(repo_root: Path) -> str:
    return (repo_root / "scripts" / "verify_odoo18_plm_stack.sh").read_text(
        encoding="utf-8",
        errors="replace",
    )


def _shell_array_entries(script_text: str, array_name: str) -> list[str]:
    match = re.search(rf"^{array_name}=\(\n(?P<body>.*?)\n\)", script_text, re.MULTILINE | re.DOTALL)
    assert match is not None, f"Missing shell array: {array_name}"
    return re.findall(r'^\s+"([^"]+)"\s*$', match.group("body"), flags=re.MULTILINE)


def test_odoo18_plm_stack_smoke_compiles_all_web_router_files() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    cd_pos = text.index('cd "$REPO_ROOT"')
    discover_pos = text.index(
        'find "src/yuantus/meta_engine/web" -maxdepth 1 -type f -name "*_router.py" | sort'
    )
    append_pos = text.index('compile_files+=("$router_file")')
    dedupe_pos = text.index("deduped_compile_files=()")
    assign_deduped_pos = text.index('compile_files=("${deduped_compile_files[@]}")')
    py_compile_pos = text.index('"$PY_BIN" -m py_compile "${compile_files[@]}"')

    assert cd_pos < discover_pos < py_compile_pos
    assert cd_pos < append_pos < py_compile_pos
    assert discover_pos < dedupe_pos < assign_deduped_pos < py_compile_pos


def test_odoo18_plm_stack_verifier_uses_strict_bash_mode() -> None:
    repo_root = _find_repo_root(Path(__file__))
    lines = _script_text(repo_root).splitlines()

    assert lines[:2] == ["#!/usr/bin/env bash", "set -euo pipefail"]


def test_odoo18_plm_stack_verifier_defaults_py_bin_to_repo_venv_then_python3() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    mode_pos = text.index('MODE="${1:-full}"')
    script_dir_pos = text.index('SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"')
    repo_root_pos = text.index('REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"')
    py_bin_init_pos = text.index('PY_BIN="${PY_BIN:-}"')
    py_bin_empty_check_pos = text.index('if [[ -z "$PY_BIN" ]]; then')
    venv_check_pos = text.index('if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then')
    venv_assign_pos = text.index('PY_BIN="${REPO_ROOT}/.venv/bin/python"')
    python3_assign_pos = text.index('PY_BIN="python3"')
    pytest_cmd_pos = text.index("PYTEST_CMD=()")

    assert mode_pos < script_dir_pos < repo_root_pos < py_bin_init_pos
    assert py_bin_init_pos < py_bin_empty_check_pos < venv_check_pos < venv_assign_pos
    assert venv_assign_pos < python3_assign_pos < pytest_cmd_pos
    assert "Defaults to .venv/bin/python when present." in text


def test_odoo18_plm_stack_verifier_anchors_execution_to_repo_root_before_work() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    mode_pos = text.index('MODE="${1:-full}"')
    script_dir_pos = text.index('SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"')
    repo_root_pos = text.index('REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"')
    cd_pos = text.index('cd "$REPO_ROOT"')
    discover_pos = text.index(
        'find "src/yuantus/meta_engine/web" -maxdepth 1 -type f -name "*_router.py" | sort'
    )
    py_compile_pos = text.index('"$PY_BIN" -m py_compile "${compile_files[@]}"')
    pytest_pos = text.index('"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"')

    assert mode_pos < script_dir_pos < repo_root_pos
    assert repo_root_pos < cd_pos < discover_pos < py_compile_pos < pytest_pos


def test_odoo18_plm_stack_verifier_defaults_no_arg_to_full_mode() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    mode_pos = text.index('MODE="${1:-full}"')
    help_pos = text.index("full   Run the broader Odoo18 PLM regression set. This is the default.")
    full_tests_pos = text.index("full_tests=(")
    mode_case_pos = text.index('case "$MODE" in', full_tests_pos)
    full_branch_pos = text.index('  full)\n    selected_tests=("${full_tests[@]}")')
    invalid_branch_pos = text.index("  *)\n    usage >&2\n    exit 2", full_branch_pos)

    assert mode_pos < help_pos < full_tests_pos < mode_case_pos
    assert mode_case_pos < full_branch_pos < invalid_branch_pos


def test_odoo18_plm_stack_verifier_validates_args_and_mode_before_repo_work() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    extra_args_pos = text.index('if [[ "$#" -gt 1 ]]; then')
    help_case_pos = text.index('case "$MODE" in')
    export_pos = text.index('export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/yuantus-pyc}"')
    full_tests_pos = text.index("full_tests=(")
    mode_case_pos = text.index('case "$MODE" in', full_tests_pos)
    invalid_branch_pos = text.index("  *)\n    usage >&2\n    exit 2", mode_case_pos)
    cd_pos = text.index('cd "$REPO_ROOT"')
    discover_pos = text.index(
        'find "src/yuantus/meta_engine/web" -maxdepth 1 -type f -name "*_router.py" | sort'
    )
    py_compile_pos = text.index('"$PY_BIN" -m py_compile "${compile_files[@]}"')
    pytest_pos = text.index('"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"')

    assert extra_args_pos < help_case_pos < export_pos
    assert export_pos < mode_case_pos < invalid_branch_pos < cd_pos
    assert cd_pos < discover_pos < py_compile_pos < pytest_pos


def test_odoo18_plm_stack_verifier_has_help_mode() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_odoo18_plm_stack.sh"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "--help"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert cp.stderr == ""
    for token in (
        "Usage: scripts/verify_odoo18_plm_stack.sh [smoke|full]",
        "smoke  Run the focused Odoo18 PLM smoke set.",
        "full   Run the broader Odoo18 PLM regression set.",
        "PY_BIN",
        "PYTEST_BIN",
        "PYTHONPYCACHEPREFIX",
    ):
        assert token in cp.stdout
    assert "[verify_odoo18_plm_stack]" not in cp.stdout


def test_odoo18_plm_stack_verifier_rejects_invalid_mode_without_running() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_odoo18_plm_stack.sh"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "invalid-mode"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert cp.stdout == ""
    assert "Usage: scripts/verify_odoo18_plm_stack.sh [smoke|full]" in cp.stderr
    assert "[verify_odoo18_plm_stack]" not in cp.stderr


def test_odoo18_plm_stack_verifier_rejects_extra_args_without_running() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_odoo18_plm_stack.sh"

    cp = subprocess.run(  # noqa: S603,S607
        ["bash", str(script), "smoke", "extra"],
        text=True,
        capture_output=True,
    )

    assert cp.returncode == 2
    assert cp.stdout == ""
    assert "Usage: scripts/verify_odoo18_plm_stack.sh [smoke|full]" in cp.stderr
    assert "[verify_odoo18_plm_stack]" not in cp.stderr


def test_odoo18_plm_stack_verifier_uses_py_bin_module_pytest_by_default() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    pytest_cmd_init_pos = text.index("PYTEST_CMD=()")
    override_branch_pos = text.index('if [[ -n "${PYTEST_BIN:-}" ]]; then')
    override_assign_pos = text.index('PYTEST_CMD=("${PYTEST_BIN}")')
    default_assign_pos = text.index('PYTEST_CMD=("${PY_BIN}" -m pytest)')
    invoke_pos = text.index('"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"')

    assert pytest_cmd_init_pos < override_branch_pos < override_assign_pos
    assert override_branch_pos < default_assign_pos < invoke_pos
    assert '"$PYTEST_BIN" -q "${selected_tests[@]}"' not in text


def test_odoo18_plm_stack_verifier_exports_pycache_prefix_before_python_work() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    export_pos = text.index('export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/yuantus-pyc}"')
    compile_array_pos = text.index("compile_files=(")
    py_compile_pos = text.index('"$PY_BIN" -m py_compile "${compile_files[@]}"')
    pytest_pos = text.index('"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"')

    assert export_pos < compile_array_pos < py_compile_pos < pytest_pos
    assert text.count("PYTHONPYCACHEPREFIX") == 3


def test_odoo18_plm_stack_verifier_runs_compile_before_pytest_and_pass_marker_last() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    mode_echo_pos = text.index('echo "[verify_odoo18_plm_stack] mode=${MODE}"')
    compile_echo_pos = text.index('echo "[verify_odoo18_plm_stack] py_compile"')
    py_compile_pos = text.index('"$PY_BIN" -m py_compile "${compile_files[@]}"')
    pytest_echo_pos = text.index('echo "[verify_odoo18_plm_stack] pytest"')
    pytest_pos = text.index('"${PYTEST_CMD[@]}" -q "${selected_tests[@]}"')
    pass_echo_pos = text.index('echo "[verify_odoo18_plm_stack] PASS"')

    assert mode_echo_pos < compile_echo_pos < py_compile_pos
    assert py_compile_pos < pytest_echo_pos < pytest_pos < pass_echo_pos


def test_odoo18_plm_stack_manual_lists_reference_existing_files() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)

    for array_name in ("compile_files", "smoke_tests", "full_tests"):
        entries = _shell_array_entries(text, array_name)
        assert entries, f"{array_name} must not be empty"

        duplicates = sorted({entry for entry in entries if entries.count(entry) > 1})
        assert duplicates == [], f"{array_name} contains duplicate entries: {duplicates}"

        missing = sorted(entry for entry in entries if not (repo_root / entry).is_file())
        assert missing == [], f"{array_name} references missing files: {missing}"


def test_odoo18_plm_stack_smoke_tests_are_subset_of_full_tests() -> None:
    repo_root = _find_repo_root(Path(__file__))
    text = _script_text(repo_root)
    smoke_tests = set(_shell_array_entries(text, "smoke_tests"))
    full_tests = set(_shell_array_entries(text, "full_tests"))

    assert sorted(smoke_tests - full_tests) == []
