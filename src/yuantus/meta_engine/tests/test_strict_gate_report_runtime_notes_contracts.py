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


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR)


def test_strict_gate_report_backfills_effective_playwright_runtime_notes(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_report.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(
        fake_pytest,
        "#!/usr/bin/env bash\n"
        "exit 0\n",
    )

    fake_runner = tmp_path / "fake_runner.sh"
    _write_executable(
        fake_runner,
        "#!/usr/bin/env bash\n"
        "echo PLAYWRIGHT_ATTEMPT=1\n"
        "echo PLAYWRIGHT_PORT=50001\n"
        "echo PLAYWRIGHT_BASE_URL=http://127.0.0.1:50001\n"
        "echo PLAYWRIGHT_DB_PATH=/tmp/fake_pw_50001.db\n"
        "echo PLAYWRIGHT_MAX_ATTEMPTS=2\n"
        "echo PLAYWRIGHT_KEEP_DB=0\n"
        "echo PLAYWRIGHT_RETRYABLE_PATTERN=PATTERN_A\n"
        "echo PLAYWRIGHT_ATTEMPT=2\n"
        "echo PLAYWRIGHT_PORT=50002\n"
        "echo PLAYWRIGHT_BASE_URL=http://127.0.0.1:50002\n"
        "echo PLAYWRIGHT_DB_PATH=/tmp/fake_pw_50002.db\n"
        "echo PLAYWRIGHT_MAX_ATTEMPTS=2\n"
        "echo PLAYWRIGHT_KEEP_DB=0\n"
        "echo PLAYWRIGHT_RETRYABLE_PATTERN=PATTERN_B\n"
        "exit 0\n",
    )

    report_path = tmp_path / "STRICT_GATE_TEST_REPORT.md"
    out_dir = tmp_path / "logs"

    env = os.environ.copy()
    env.update(
        {
            "PYTEST_BIN": str(fake_pytest),
            "PLAYWRIGHT_RUNNER": str(fake_runner),
            "RUN_ID": "STRICT_GATE_TEST_NOTES",
            "OUT_DIR": str(out_dir),
            "REPORT_PATH": str(report_path),
        }
    )
    env.pop("PLAYWRIGHT_PORT", None)
    env.pop("PLAYWRIGHT_BASE_URL", None)
    env.pop("PLAYWRIGHT_DB_PATH", None)

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert report_path.is_file(), "strict_gate_report.sh did not create report file"
    report = report_path.read_text(encoding="utf-8", errors="replace")

    assert "- `PLAYWRIGHT_ATTEMPT_LAST`: `2`" in report
    assert "- `PLAYWRIGHT_RETRYABLE_PATTERN`: `<unset>`" in report
    assert "- `PLAYWRIGHT_PORT`: `50002`" in report
    assert "- `PLAYWRIGHT_BASE_URL`: `http://127.0.0.1:50002`" in report
    assert "- `PLAYWRIGHT_DB_PATH`: `/tmp/fake_pw_50002.db`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST`: `2`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT`: `2`" in report
    assert "- `PLAYWRIGHT_RETRIED`: `true`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_PORT`: `50002`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_BASE_URL`: `http://127.0.0.1:50002`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_DB_PATH`: `/tmp/fake_pw_50002.db`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS`: `2`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_KEEP_DB`: `0`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN`: `PATTERN_B`" in report
    assert "- `PLAYWRIGHT_REQUESTED_MAX_ATTEMPTS`: `<unset>`" in report
    assert "- `PLAYWRIGHT_REQUESTED_RETRYABLE_PATTERN`: `<unset>`" in report
    assert "- `PLAYWRIGHT_REQUESTED_KEEP_DB`: `<unset>`" in report
    assert "- `PLAYWRIGHT_REQUESTED_PORT_PICKER_CMD`: `<unset>`" in report


def test_strict_gate_report_keeps_explicit_playwright_notes_values(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_report.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_pytest = tmp_path / "fake_pytest.sh"
    _write_executable(
        fake_pytest,
        "#!/usr/bin/env bash\n"
        "exit 0\n",
    )

    fake_runner = tmp_path / "fake_runner.sh"
    _write_executable(
        fake_runner,
        "#!/usr/bin/env bash\n"
        "echo PLAYWRIGHT_ATTEMPT=1\n"
        "echo PLAYWRIGHT_PORT=59999\n"
        "echo PLAYWRIGHT_BASE_URL=http://127.0.0.1:59999\n"
        "echo PLAYWRIGHT_DB_PATH=/tmp/fake_pw_59999.db\n"
        "echo PLAYWRIGHT_MAX_ATTEMPTS=9\n"
        "echo PLAYWRIGHT_KEEP_DB=1\n"
        "echo PLAYWRIGHT_RETRYABLE_PATTERN=RUNNER_PATTERN\n"
        "exit 0\n",
    )

    report_path = tmp_path / "STRICT_GATE_TEST_REPORT_EXPLICIT.md"
    out_dir = tmp_path / "logs-explicit"

    env = os.environ.copy()
    env.update(
        {
            "PYTEST_BIN": str(fake_pytest),
            "PLAYWRIGHT_RUNNER": str(fake_runner),
            "PLAYWRIGHT_PORT": "51111",
            "PLAYWRIGHT_BASE_URL": "http://127.0.0.1:51111",
            "PLAYWRIGHT_DB_PATH": "/tmp/explicit_pw_51111.db",
            "PLAYWRIGHT_RETRYABLE_PATTERN": "EXPLICIT_PATTERN",
            "RUN_ID": "STRICT_GATE_TEST_NOTES_EXPLICIT",
            "OUT_DIR": str(out_dir),
            "REPORT_PATH": str(report_path),
        }
    )

    cp = subprocess.run(  # noqa: S603
        ["bash", str(script)],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert report_path.is_file(), "strict_gate_report.sh did not create report file"
    report = report_path.read_text(encoding="utf-8", errors="replace")

    assert "- `PLAYWRIGHT_ATTEMPT_LAST`: `1`" in report
    assert "- `PLAYWRIGHT_RETRYABLE_PATTERN`: `EXPLICIT_PATTERN`" in report
    assert "- `PLAYWRIGHT_PORT`: `51111`" in report
    assert "- `PLAYWRIGHT_BASE_URL`: `http://127.0.0.1:51111`" in report
    assert "- `PLAYWRIGHT_DB_PATH`: `/tmp/explicit_pw_51111.db`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_ATTEMPT_LAST`: `1`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_ATTEMPT_COUNT`: `1`" in report
    assert "- `PLAYWRIGHT_RETRIED`: `false`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_PORT`: `59999`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_BASE_URL`: `http://127.0.0.1:59999`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_DB_PATH`: `/tmp/fake_pw_59999.db`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_MAX_ATTEMPTS`: `9`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_KEEP_DB`: `1`" in report
    assert "- `PLAYWRIGHT_EFFECTIVE_RETRYABLE_PATTERN`: `RUNNER_PATTERN`" in report
    assert "- `PLAYWRIGHT_REQUESTED_RETRYABLE_PATTERN`: `EXPLICIT_PATTERN`" in report
    assert "- `PLAYWRIGHT_REQUESTED_PORT`: `51111`" in report
    assert "- `PLAYWRIGHT_REQUESTED_BASE_URL`: `http://127.0.0.1:51111`" in report
    assert "- `PLAYWRIGHT_REQUESTED_DB_PATH`: `/tmp/explicit_pw_51111.db`" in report
