from __future__ import annotations

import os
import stat
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
    raise AssertionError("Could not locate repo root (expected pyproject.toml + scripts/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _runner_env(**overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PLAYWRIGHT_PORT_PICKER_CMD", "printf 39091")
    env.update(overrides)
    return env


def test_playwright_runner_has_isolated_defaults_and_retry_logic() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"
    text = _read(runner)

    for token in (
        'PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD:-npx playwright test --workers=1}"',
        'PLAYWRIGHT_MAX_ATTEMPTS="${PLAYWRIGHT_MAX_ATTEMPTS:-2}"',
        'PLAYWRIGHT_RETRYABLE_PATTERN="${PLAYWRIGHT_RETRYABLE_PATTERN:-error while attempting to bind on address|address already in use|operation not permitted}"',
        'PLAYWRIGHT_PORT_PICKER_CMD="${PLAYWRIGHT_PORT_PICKER_CMD:-}"',
        'PLAYWRIGHT_KEEP_DB="${PLAYWRIGHT_KEEP_DB:-0}"',
        'db_path="${YUANTUS_PLAYWRIGHT_DB_PATH:-/tmp/yuantus_playwright_${port}_$$.db}"',
        'bash -lc "$PLAYWRIGHT_PORT_PICKER_CMD"',
        'env PORT="$port" BASE_URL="$base_url" YUANTUS_PLAYWRIGHT_DB_PATH="$db_path" bash -lc "$PLAYWRIGHT_CMD"',
        'grep -Eqi "$PLAYWRIGHT_RETRYABLE_PATTERN"',
        'rm -f "$db_path" "${db_path}-shm" "${db_path}-wal"',
        'echo "PLAYWRIGHT_MAX_ATTEMPTS=${PLAYWRIGHT_MAX_ATTEMPTS}"',
        'echo "PLAYWRIGHT_KEEP_DB=${PLAYWRIGHT_KEEP_DB}"',
        "PLAYWRIGHT_KEEP_DB must be one of 0/1/true/false/yes/no/on/off",
        "python3 is required to allocate a free localhost port",
        "Playwright retry: detected retryable bind/startup failure",
    ):
        assert token in text, f"run_playwright_strict_gate.sh missing token: {token!r}"


def test_playwright_runner_has_help_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner), "--help"],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    out = cp.stdout or ""
    for token in (
        "Usage:",
        "run_playwright_strict_gate.sh",
        "PLAYWRIGHT_CMD",
        "PLAYWRIGHT_MAX_ATTEMPTS",
        "PLAYWRIGHT_RETRYABLE_PATTERN",
        "PLAYWRIGHT_PORT",
        "PLAYWRIGHT_PORT_PICKER_CMD",
        "PLAYWRIGHT_BASE_URL",
        "YUANTUS_PLAYWRIGHT_DB_PATH",
        "PLAYWRIGHT_KEEP_DB",
    ):
        assert token in out, f"run_playwright_strict_gate.sh help missing token: {token!r}"


def test_strict_gate_scripts_use_playwright_runner_contract() -> None:
    repo_root = _find_repo_root(Path(__file__))
    strict_gate = repo_root / "scripts" / "strict_gate.sh"
    strict_gate_report = repo_root / "scripts" / "strict_gate_report.sh"
    assert strict_gate.is_file(), f"Missing {strict_gate}"
    assert strict_gate_report.is_file(), f"Missing {strict_gate_report}"
    strict_text = _read(strict_gate)
    report_text = _read(strict_gate_report)

    for token in (
        'PLAYWRIGHT_RUNNER="${PLAYWRIGHT_RUNNER:-${REPO_ROOT}/scripts/run_playwright_strict_gate.sh}"',
        'PLAYWRIGHT_CMD="${PLAYWRIGHT_CMD:-npx playwright test --workers=1}"',
        'PLAYWRIGHT_MAX_ATTEMPTS="${PLAYWRIGHT_MAX_ATTEMPTS:-2}"',
        'PLAYWRIGHT_RETRYABLE_PATTERN="${PLAYWRIGHT_RETRYABLE_PATTERN:-}"',
        'PLAYWRIGHT_PORT_PICKER_CMD="${PLAYWRIGHT_PORT_PICKER_CMD:-}"',
        'PLAYWRIGHT_KEEP_DB="${PLAYWRIGHT_KEEP_DB:-0}"',
        'ERROR: PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer, got: ${PLAYWRIGHT_MAX_ATTEMPTS}',
        'ERROR: PLAYWRIGHT_RETRYABLE_PATTERN is not a valid extended regex: ${PLAYWRIGHT_RETRYABLE_PATTERN}',
        'ERROR: PLAYWRIGHT_KEEP_DB must be one of 0/1/true/false/yes/no/on/off, got: ${PLAYWRIGHT_KEEP_DB}',
        'ERROR: playwright runner not found or not executable at $PLAYWRIGHT_RUNNER',
        'PLAYWRIGHT_PORT_PICKER_CMD="$PLAYWRIGHT_PORT_PICKER_CMD"',
        'YUANTUS_PLAYWRIGHT_DB_PATH="$PLAYWRIGHT_DB_PATH"',
        'PLAYWRIGHT_MAX_ATTEMPTS="$PLAYWRIGHT_MAX_ATTEMPTS"',
        'PLAYWRIGHT_RETRYABLE_PATTERN="$PLAYWRIGHT_RETRYABLE_PATTERN"',
        'PLAYWRIGHT_KEEP_DB="$PLAYWRIGHT_KEEP_DB"',
    ):
        assert token in strict_text, f"strict_gate.sh missing token: {token!r}"
        assert token in report_text, f"strict_gate_report.sh missing token: {token!r}"

    for token in (
        'run_id="${RUN_ID:-STRICT_GATE_${timestamp}_$$}"',
        'report_default="${REPO_ROOT}/docs/DAILY_REPORTS/${run_id}.md"',
        r'- \`PLAYWRIGHT_RUNNER\`: \`${PLAYWRIGHT_RUNNER}\`',
        r'- \`PLAYWRIGHT_MAX_ATTEMPTS\`: \`${PLAYWRIGHT_MAX_ATTEMPTS}\`',
        r'- \`PLAYWRIGHT_RETRYABLE_PATTERN\`: \`${PLAYWRIGHT_RETRYABLE_PATTERN:-<unset>}\`',
        r'- \`PLAYWRIGHT_ATTEMPT_LAST\`: \`${PLAYWRIGHT_ATTEMPT_LAST:-<unset>}\`',
        r'- \`PLAYWRIGHT_KEEP_DB\`: \`${PLAYWRIGHT_KEEP_DB}\`',
        r'- \`PLAYWRIGHT_DB_PATH\`: \`${PLAYWRIGHT_DB_PATH:-<unset>}\`',
        r'- \`PLAYWRIGHT_PORT_PICKER_CMD\`: \`${PLAYWRIGHT_PORT_PICKER_CMD:-<unset>}\`',
        r'- \`PLAYWRIGHT_REQUESTED_PORT_PICKER_CMD\`: \`${REQUESTED_PLAYWRIGHT_PORT_PICKER_CMD}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST\`: \`${PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST:-<unset>}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT\`: \`${PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT:-<unset>}\`',
        r'- \`PLAYWRIGHT_RETRIED\`: \`${PLAYWRIGHT_RETRIED}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_PORT\`: \`${PLAYWRIGHT_EFFECTIVE_PORT:-<unset>}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_BASE_URL\`: \`${PLAYWRIGHT_EFFECTIVE_BASE_URL:-<unset>}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_DB_PATH\`: \`${PLAYWRIGHT_EFFECTIVE_DB_PATH:-<unset>}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS\`: \`${PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS:-<unset>}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_KEEP_DB\`: \`${PLAYWRIGHT_EFFECTIVE_KEEP_DB:-<unset>}\`',
        r'- \`PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN\`: \`${PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN:-<unset>}\`',
        "PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST=\"$(grep -E '^PLAYWRIGHT_ATTEMPT='",
        "PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT=\"$(grep -c -E '^PLAYWRIGHT_ATTEMPT='",
        "PLAYWRIGHT_EFFECTIVE_PORT=\"$(grep -E '^PLAYWRIGHT_PORT='",
        "PLAYWRIGHT_EFFECTIVE_BASE_URL=\"$(grep -E '^PLAYWRIGHT_BASE_URL='",
        "PLAYWRIGHT_EFFECTIVE_DB_PATH=\"$(grep -E '^PLAYWRIGHT_DB_PATH='",
        "PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS=\"$(grep -E '^PLAYWRIGHT_MAX_ATTEMPTS='",
        "PLAYWRIGHT_EFFECTIVE_KEEP_DB=\"$(grep -E '^PLAYWRIGHT_KEEP_DB='",
        "PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN=\"$(grep -E '^PLAYWRIGHT_RETRYABLE_PATTERN='",
    ):
        assert token in report_text, f"strict_gate_report.sh missing token: {token!r}"


def test_playwright_runner_retries_once_for_bind_like_failure(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    count_file = tmp_path / "attempt.count"
    cmd = (
        f'count_file="{count_file}"; '
        'n=0; '
        'if [[ -f "$count_file" ]]; then n=$(cat "$count_file"); fi; '
        'n=$((n+1)); '
        'echo "$n" > "$count_file"; '
        'if [[ "$n" -eq 1 ]]; then '
        'echo "error while attempting to bind on address (\'127.0.0.1\', 7910): operation not permitted"; '
        "exit 1; "
        "fi; "
        'echo "runner-success"; '
        "exit 0"
    )

    env = _runner_env(
        PLAYWRIGHT_CMD=cmd,
        PLAYWRIGHT_MAX_ATTEMPTS="2",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 0, out
    assert "PLAYWRIGHT_ATTEMPT=1" in out
    assert "PLAYWRIGHT_ATTEMPT=2" in out
    assert "Playwright retry: detected retryable bind/startup failure" in out
    assert "runner-success" in out
    assert count_file.read_text(encoding="utf-8").strip() == "2"


def test_playwright_runner_does_not_retry_non_retryable_failure(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    count_file = tmp_path / "attempt.count"
    cmd = (
        f'count_file="{count_file}"; '
        'n=0; '
        'if [[ -f "$count_file" ]]; then n=$(cat "$count_file"); fi; '
        'n=$((n+1)); '
        'echo "$n" > "$count_file"; '
        'echo "fatal: unrelated failure"; '
        "exit 7"
    )

    env = _runner_env(
        PLAYWRIGHT_CMD=cmd,
        PLAYWRIGHT_MAX_ATTEMPTS="3",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 7, out
    assert "PLAYWRIGHT_ATTEMPT=1" in out
    assert "PLAYWRIGHT_ATTEMPT=2" not in out
    assert "Playwright retry: detected retryable bind/startup failure" not in out
    assert count_file.read_text(encoding="utf-8").strip() == "1"


def test_playwright_runner_cleans_db_files_by_default(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    db_path = tmp_path / "pw.db"
    cmd = (
        'echo "ok" > "$YUANTUS_PLAYWRIGHT_DB_PATH"; '
        'echo "ok" > "${YUANTUS_PLAYWRIGHT_DB_PATH}-shm"; '
        'echo "ok" > "${YUANTUS_PLAYWRIGHT_DB_PATH}-wal"; '
        "exit 0"
    )
    env = _runner_env(
        PLAYWRIGHT_CMD=cmd,
        YUANTUS_PLAYWRIGHT_DB_PATH=str(db_path),
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 0, out
    assert not db_path.exists()
    assert not Path(f"{db_path}-shm").exists()
    assert not Path(f"{db_path}-wal").exists()


def test_playwright_runner_keeps_db_files_when_requested(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    db_path = tmp_path / "pw-keep.db"
    cmd = (
        'echo "ok" > "$YUANTUS_PLAYWRIGHT_DB_PATH"; '
        'echo "ok" > "${YUANTUS_PLAYWRIGHT_DB_PATH}-shm"; '
        'echo "ok" > "${YUANTUS_PLAYWRIGHT_DB_PATH}-wal"; '
        "exit 0"
    )
    env = _runner_env(
        PLAYWRIGHT_CMD=cmd,
        YUANTUS_PLAYWRIGHT_DB_PATH=str(db_path),
        PLAYWRIGHT_KEEP_DB="1",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 0, out
    assert db_path.exists()
    assert Path(f"{db_path}-shm").exists()
    assert Path(f"{db_path}-wal").exists()


def test_playwright_runner_rejects_zero_max_attempts() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    env = _runner_env(
        PLAYWRIGHT_MAX_ATTEMPTS="0",
        PLAYWRIGHT_CMD="echo should-not-run; exit 0",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer" in out


def test_playwright_runner_rejects_non_numeric_max_attempts() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    env = _runner_env(
        PLAYWRIGHT_MAX_ATTEMPTS="abc",
        PLAYWRIGHT_CMD="echo should-not-run; exit 0",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer" in out


def test_playwright_runner_rejects_invalid_keep_db() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    env = _runner_env(
        PLAYWRIGHT_KEEP_DB="maybe",
        PLAYWRIGHT_CMD="echo should-not-run; exit 0",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_KEEP_DB must be one of 0/1/true/false/yes/no/on/off" in out


def test_playwright_runner_retries_on_custom_pattern(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    count_file = tmp_path / "attempt_custom.count"
    cmd = (
        f'count_file="{count_file}"; '
        'n=0; '
        'if [[ -f "$count_file" ]]; then n=$(cat "$count_file"); fi; '
        'n=$((n+1)); '
        'echo "$n" > "$count_file"; '
        'if [[ "$n" -eq 1 ]]; then '
        'echo "CUSTOM_RETRY_MARKER"; '
        "exit 1; "
        "fi; "
        'echo "custom-retry-success"; '
        "exit 0"
    )

    env = _runner_env(
        PLAYWRIGHT_CMD=cmd,
        PLAYWRIGHT_MAX_ATTEMPTS="2",
        PLAYWRIGHT_RETRYABLE_PATTERN="CUSTOM_RETRY_MARKER",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 0, out
    assert "PLAYWRIGHT_ATTEMPT=2" in out
    assert "custom-retry-success" in out
    assert count_file.read_text(encoding="utf-8").strip() == "2"


def test_playwright_runner_uses_default_pattern_when_retryable_pattern_empty() -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    env = _runner_env(
        PLAYWRIGHT_RETRYABLE_PATTERN="",
        PLAYWRIGHT_CMD="echo pattern-fallback-ok; exit 0",
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 0, out
    assert "pattern-fallback-ok" in out
    assert "PLAYWRIGHT_RETRYABLE_PATTERN=error while attempting to bind on address|address already in use|operation not permitted" in out


def test_playwright_runner_rejects_invalid_retryable_pattern_before_command(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    runner = repo_root / "scripts" / "run_playwright_strict_gate.sh"
    assert runner.is_file(), f"Missing {runner}"

    marker = tmp_path / "runner_cmd.marker"
    env = _runner_env(
        PLAYWRIGHT_RETRYABLE_PATTERN="(",
        PLAYWRIGHT_CMD=f'echo "ran" > "{marker}"; exit 0',
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(runner)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_RETRYABLE_PATTERN is not a valid extended regex" in out
    assert not marker.exists(), "runner should fail before invoking PLAYWRIGHT_CMD"


def test_strict_gate_rejects_missing_playwright_runner(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate.sh"
    assert script.is_file(), f"Missing {script}"

    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(fake_pytest, "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env["PYTEST_BIN"] = str(fake_pytest)
    env["PLAYWRIGHT_RUNNER"] = str(tmp_path / "missing_runner.sh")

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "playwright runner not found or not executable" in out


def test_strict_gate_report_rejects_missing_playwright_runner(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_report.sh"
    assert script.is_file(), f"Missing {script}"

    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(fake_pytest, "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env["PYTEST_BIN"] = str(fake_pytest)
    env["PLAYWRIGHT_RUNNER"] = str(tmp_path / "missing_runner.sh")
    env["RUN_ID"] = "STRICT_GATE_TEST_MISSING_RUNNER"
    env["OUT_DIR"] = str(tmp_path / "logs")
    env["REPORT_PATH"] = str(tmp_path / "report.md")

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "playwright runner not found or not executable" in out


def test_strict_gate_rejects_invalid_max_attempts_before_pytests(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate.sh"
    assert script.is_file(), f"Missing {script}"

    marker = tmp_path / "pytest_ran.marker"
    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(
        fake_pytest,
        "#!/usr/bin/env bash\n"
        f'echo "ran" > "{marker}"\n'
        "exit 0\n",
    )
    fake_runner = tmp_path / "fake_runner.sh"
    _write_executable(fake_runner, "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env["PYTEST_BIN"] = str(fake_pytest)
    env["PLAYWRIGHT_RUNNER"] = str(fake_runner)
    env["PLAYWRIGHT_MAX_ATTEMPTS"] = "0"

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer" in out
    assert not marker.exists(), "strict_gate.sh should fail before invoking pytest"


def test_strict_gate_report_rejects_invalid_max_attempts_before_pytests(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_report.sh"
    assert script.is_file(), f"Missing {script}"

    marker = tmp_path / "pytest_ran.marker"
    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(
        fake_pytest,
        "#!/usr/bin/env bash\n"
        f'echo "ran" > "{marker}"\n'
        "exit 0\n",
    )
    fake_runner = tmp_path / "fake_runner.sh"
    _write_executable(fake_runner, "#!/usr/bin/env bash\nexit 0\n")
    report_path = tmp_path / "report.md"

    env = os.environ.copy()
    env["PYTEST_BIN"] = str(fake_pytest)
    env["PLAYWRIGHT_RUNNER"] = str(fake_runner)
    env["PLAYWRIGHT_MAX_ATTEMPTS"] = "abc"
    env["RUN_ID"] = "STRICT_GATE_TEST_INVALID_ATTEMPTS"
    env["OUT_DIR"] = str(tmp_path / "logs")
    env["REPORT_PATH"] = str(report_path)

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_MAX_ATTEMPTS must be a positive integer" in out
    assert not marker.exists(), "strict_gate_report.sh should fail before invoking pytest"
    assert not report_path.exists(), "report should not be generated on early validation failure"


def test_strict_gate_rejects_invalid_retry_pattern_before_pytests(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate.sh"
    assert script.is_file(), f"Missing {script}"

    marker = tmp_path / "pytest_ran_invalid_pattern.marker"
    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(
        fake_pytest,
        "#!/usr/bin/env bash\n"
        f'echo "ran" > "{marker}"\n'
        "exit 0\n",
    )
    fake_runner = tmp_path / "fake_runner.sh"
    _write_executable(fake_runner, "#!/usr/bin/env bash\nexit 0\n")

    env = os.environ.copy()
    env["PYTEST_BIN"] = str(fake_pytest)
    env["PLAYWRIGHT_RUNNER"] = str(fake_runner)
    env["PLAYWRIGHT_RETRYABLE_PATTERN"] = "("

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_RETRYABLE_PATTERN is not a valid extended regex" in out
    assert not marker.exists(), "strict_gate.sh should fail before invoking pytest"


def test_strict_gate_report_rejects_invalid_retry_pattern_before_pytests(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_report.sh"
    assert script.is_file(), f"Missing {script}"

    marker = tmp_path / "pytest_ran_invalid_pattern.marker"
    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(
        fake_pytest,
        "#!/usr/bin/env bash\n"
        f'echo "ran" > "{marker}"\n'
        "exit 0\n",
    )
    fake_runner = tmp_path / "fake_runner.sh"
    _write_executable(fake_runner, "#!/usr/bin/env bash\nexit 0\n")
    report_path = tmp_path / "report_invalid_pattern.md"

    env = os.environ.copy()
    env["PYTEST_BIN"] = str(fake_pytest)
    env["PLAYWRIGHT_RUNNER"] = str(fake_runner)
    env["PLAYWRIGHT_RETRYABLE_PATTERN"] = "("
    env["RUN_ID"] = "STRICT_GATE_TEST_INVALID_PATTERN"
    env["OUT_DIR"] = str(tmp_path / "logs-invalid-pattern")
    env["REPORT_PATH"] = str(report_path)

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        cwd=repo_root,
        text=True,
        capture_output=True,
        env=env,
    )
    out = (cp.stdout or "") + (cp.stderr or "")
    assert cp.returncode == 2, out
    assert "PLAYWRIGHT_RETRYABLE_PATTERN is not a valid extended regex" in out
    assert not marker.exists(), "strict_gate_report.sh should fail before invoking pytest"
    assert not report_path.exists(), "report should not be generated on early validation failure"
