from __future__ import annotations

import json
import os
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


def test_strict_gate_perf_download_and_trend_with_fake_gh(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    rows = [
        {"databaseId": 101, "status": "completed", "conclusion": "failure"},
        {"databaseId": 100, "status": "completed", "conclusion": "success"},
    ]
    print(json.dumps(rows))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    artifact_name = ""
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        if args[i] == "-n" and i + 1 < len(args):
            artifact_name = args[i + 1]
            i += 2
            continue
        i += 1

    if artifact_name != "strict-gate-perf-summary":
        raise SystemExit(1)

    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    if run_id == "101":
        status = "FAIL"
        p95 = "1900.000"
    else:
        status = "PASS"
        p95 = "100.000"
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            f"| release_orchestration.plan | {status} | {p95} | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "2",
            "--branch",
            "main",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
            "--include-empty",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Downloaded artifacts: 2" in cp.stdout
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    out = trend_out.read_text(encoding="utf-8", errors="replace")
    # Latest run id should appear first.
    assert out.index("`STRICT_GATE_CI_101`") < out.index("`STRICT_GATE_CI_100`")
    assert "| `STRICT_GATE_CI_101` | FAIL |" in out
    assert "FAIL 1900.000/1800.000" in out

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["artifact_name"] == "strict-gate-perf-summary"
    assert payload["download_retries"] == 1
    assert payload["download_retry_delay_sec"] == 1
    assert payload["downloaded_count"] == 2
    assert payload["skipped_count"] == 0
    assert payload["perf_report_count"] == 2
    assert payload["metric_report_count"] == 2
    assert payload["no_metric_report_count"] == 0
    assert payload["run_id_mode"] is False
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["fail_if_none_downloaded"] is False
    assert payload["failed_due_to_zero_downloads"] is False
    assert payload["clean_download_dir"] is False
    assert payload["selected_run_ids"] == ["101", "100"]
    assert payload["downloaded_run_ids"] == ["101", "100"]
    assert payload["skipped_run_ids"] == []
    assert payload["run_results"] == [
        {"run_id": "101", "downloaded": True, "attempts": 1},
        {"run_id": "100", "downloaded": True, "attempts": 1},
    ]


def test_strict_gate_perf_download_and_trend_with_custom_artifact_name(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([{"databaseId": 501, "status": "completed", "conclusion": "success"}]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    artifact_name = ""
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        if args[i] == "-n" and i + 1 < len(args):
            artifact_name = args[i + 1]
            i += 2
            continue
        i += 1

    if artifact_name != "custom-perf-artifact":
        raise SystemExit(1)

    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            f"| release_orchestration.plan | {'PASS' if run_id == '501' else 'FAIL'} | 100.000 | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--artifact-name",
            "custom-perf-artifact",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Download artifact custom-perf-artifact" in cp.stdout
    assert "Downloaded artifacts: 1" in cp.stdout
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["artifact_name"] == "custom-perf-artifact"
    assert payload["download_retries"] == 1
    assert payload["download_retry_delay_sec"] == 1
    assert payload["downloaded_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["perf_report_count"] == 1
    assert payload["metric_report_count"] == 1
    assert payload["no_metric_report_count"] == 0
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["fail_if_none_downloaded"] is False
    assert payload["failed_due_to_zero_downloads"] is False
    assert payload["clean_download_dir"] is False
    assert payload["selected_run_ids"] == ["501"]
    assert payload["downloaded_run_ids"] == ["501"]
    assert payload["run_results"] == [{"run_id": "501", "downloaded": True, "attempts": 1}]


def test_strict_gate_perf_download_and_trend_normalizes_flat_artifact_layout(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([{"databaseId": 777, "status": "completed", "conclusion": "success"}]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    out_dir = "."
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        i += 1

    # Flat layout (no docs/DAILY_REPORTS nesting), as observed with some artifacts.
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            "| release_orchestration.plan | PASS | 100.000 | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / "STRICT_GATE_CI_777_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Downloaded artifacts: 1" in cp.stdout
    assert "Discovered perf files: 1 (normalized copies: 1)" in cp.stdout
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    normalized = download_dir / "docs" / "DAILY_REPORTS" / "STRICT_GATE_CI_777_PERF.md"
    assert normalized.is_file(), f"Missing normalized perf report: {normalized}"

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["discovered_perf_files"] == 1
    assert payload["normalized_perf_files"] == 1
    assert payload["perf_report_count"] == 1
    assert payload["metric_report_count"] == 1
    assert payload["no_metric_report_count"] == 0
    assert payload["selected_run_ids"] == ["777"]
    assert payload["downloaded_run_ids"] == ["777"]


def test_strict_gate_perf_download_and_trend_with_conclusion_filter(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    rows = [
        {"databaseId": 301, "status": "completed", "conclusion": "failure"},
        {"databaseId": 300, "status": "completed", "conclusion": "success"},
    ]
    print(json.dumps(rows))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        i += 1
    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            f"| release_orchestration.plan | {'PASS' if run_id == '300' else 'FAIL'} | {'100.000' if run_id == '300' else '1900.000'} | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "2",
            "--conclusion",
            "success",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Downloaded artifacts: 1" in cp.stdout
    out = trend_out.read_text(encoding="utf-8", errors="replace")
    assert "`STRICT_GATE_CI_300`" in out
    assert "`STRICT_GATE_CI_301`" not in out


def test_strict_gate_perf_download_and_trend_run_id_mode_skips_list(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    # run-id mode should bypass run list entirely.
    print("run list should not be called in --run-id mode", file=sys.stderr)
    raise SystemExit(3)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        i += 1
    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            "| release_orchestration.plan | PASS | 100.000 | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--run-id",
            "888",
            "--conclusion",
            "success",
            "--max-run-age-days",
            "7",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Use explicit run ids: 888" in cp.stdout
    assert "Downloaded artifacts: 1" in cp.stdout
    assert "--conclusion is ignored when --run-id is explicitly provided." in cp.stderr
    assert "--max-run-age-days is ignored when --run-id is explicitly provided." in cp.stderr
    out = trend_out.read_text(encoding="utf-8", errors="replace")
    assert "`STRICT_GATE_CI_888`" in out


def test_strict_gate_perf_download_and_trend_retries_download_once(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    attempt_file = tmp_path / "download_attempts.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([{"databaseId": 901, "status": "completed", "conclusion": "failure"}]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        i += 1

    attempts_path = Path("ATTEMPT_FILE")
    attempt = 0
    if attempts_path.exists():
        raw = attempts_path.read_text(encoding="utf-8").strip()
        if raw:
            attempt = int(raw)
    attempt += 1
    attempts_path.write_text(str(attempt), encoding="utf-8")

    if attempt == 1:
        raise SystemExit(1)

    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            f"| release_orchestration.plan | {'PASS' if run_id == '901' else 'FAIL'} | 100.000 | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""".replace("ATTEMPT_FILE", str(attempt_file)),
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--download-retries",
            "2",
            "--download-retry-delay-sec",
            "0",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Downloaded artifacts: 1" in cp.stdout
    assert "download attempt 1/2 failed for run_id=901; retry in 0s." in cp.stderr
    assert attempt_file.read_text(encoding="utf-8").strip() == "2"
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["download_retries"] == 2
    assert payload["download_retry_delay_sec"] == 0
    assert payload["downloaded_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["perf_report_count"] == 1
    assert payload["metric_report_count"] == 1
    assert payload["no_metric_report_count"] == 0
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["clean_download_dir"] is False
    assert payload["downloaded_run_ids"] == ["901"]
    assert payload["run_results"] == [{"run_id": "901", "downloaded": True, "attempts": 2}]


def test_strict_gate_perf_download_and_trend_clean_download_dir(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([{"databaseId": 990, "status": "completed", "conclusion": "success"}]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        i += 1
    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            f"| release_orchestration.plan | {'PASS' if run_id == '990' else 'FAIL'} | 120.000 | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    stale_path = download_dir / "docs" / "DAILY_REPORTS" / "STRICT_GATE_CI_777_PERF.md"
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text(
        "\n".join(
            [
                "## Perf Smoke Summary",
                "",
                "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
                "| --- | --- | --- | --- | --- | --- |",
                "| release_orchestration.plan | FAIL | 2500.000 | 1800.000 | 5 | `stale` |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--clean-download-dir",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert f"Clean download dir: {download_dir}" in cp.stdout
    assert stale_path.exists() is False
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    out = trend_out.read_text(encoding="utf-8", errors="replace")
    assert "`STRICT_GATE_CI_990`" in out
    assert "`STRICT_GATE_CI_777`" not in out

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["clean_download_dir"] is True
    assert payload["downloaded_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["perf_report_count"] == 1
    assert payload["metric_report_count"] == 1
    assert payload["no_metric_report_count"] == 0
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["selected_run_ids"] == ["990"]


def test_strict_gate_perf_download_and_trend_clean_download_dir_rejects_repo_root(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import sys

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

# should not reach run list/download when clean path safety check fails first.
raise SystemExit(9)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--clean-download-dir",
            "--download-dir",
            str(repo_root),
            "--limit",
            "1",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 2, cp.stdout + "\n" + cp.stderr
    assert "ERROR: refusing to clean unsafe --download-dir:" in cp.stderr


def test_strict_gate_perf_download_and_trend_with_max_run_age_days_filter(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    rows = [
        {"databaseId": 880, "status": "completed", "conclusion": "success", "createdAt": "2000-01-01T00:00:00Z"},
        {"databaseId": 881, "status": "completed", "conclusion": "success", "createdAt": "2099-01-01T00:00:00Z"},
        {"databaseId": 882, "status": "completed", "conclusion": "success"},
        {"databaseId": 883, "status": "completed", "conclusion": "success", "createdAt": "bad-ts"},
    ]
    print(json.dumps(rows))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        i += 1
    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "| Metric | Status | p95 (ms) | Threshold (ms) | Samples | Source |",
            "| --- | --- | --- | --- | --- | --- |",
            f"| release_orchestration.plan | {'PASS' if run_id == '881' else 'FAIL'} | 100.000 | 1800.000 | 5 | `dummy` |",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "2",
            "--max-run-age-days",
            "7",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "Downloaded artifacts: 1" in cp.stdout
    assert "max_run_age_days=7" in cp.stdout
    out = trend_out.read_text(encoding="utf-8", errors="replace")
    assert "`STRICT_GATE_CI_881`" in out
    assert "`STRICT_GATE_CI_880`" not in out
    assert "`STRICT_GATE_CI_882`" not in out
    assert "`STRICT_GATE_CI_883`" not in out

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] == 7
    assert payload["downloaded_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["perf_report_count"] == 1
    assert payload["metric_report_count"] == 1
    assert payload["no_metric_report_count"] == 0
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["selected_run_ids"] == ["881"]
    assert payload["run_results"] == [{"run_id": "881", "downloaded": True, "attempts": 1}]


def test_strict_gate_perf_download_and_trend_rejects_negative_max_run_age_days(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--max-run-age-days",
            "-1",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert cp.returncode == 2, cp.stdout + "\n" + cp.stderr
    assert "ERROR: --max-run-age-days must be a non-negative integer" in cp.stderr


def test_strict_gate_perf_download_and_trend_rejects_non_numeric_max_run_age_days(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--max-run-age-days",
            "abc",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert cp.returncode == 2, cp.stdout + "\n" + cp.stderr
    assert "ERROR: --max-run-age-days must be a non-negative integer" in cp.stderr


def test_strict_gate_perf_download_and_trend_rejects_zero_download_retries(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--download-retries",
            "0",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert cp.returncode == 2, cp.stdout + "\n" + cp.stderr
    assert "ERROR: --download-retries must be a positive integer" in cp.stderr


def test_strict_gate_perf_download_and_trend_rejects_negative_download_retry_delay(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--download-retry-delay-sec",
            "-1",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert cp.returncode == 2, cp.stdout + "\n" + cp.stderr
    assert "ERROR: --download-retry-delay-sec must be a non-negative integer" in cp.stderr


def test_strict_gate_perf_download_and_trend_rejects_non_numeric_download_retry_delay(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--download-retry-delay-sec",
            "abc",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert cp.returncode == 2, cp.stdout + "\n" + cp.stderr
    assert "ERROR: --download-retry-delay-sec must be a non-negative integer" in cp.stderr


def test_strict_gate_perf_download_and_trend_fail_if_none_downloaded(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([{"databaseId": 700, "status": "completed", "conclusion": "failure"}]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    # Simulate artifact not found for all selected runs.
    raise SystemExit(1)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--fail-if-none-downloaded",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 1, cp.stdout + "\n" + cp.stderr
    assert "Downloaded artifacts: 0" in cp.stdout
    assert "ERROR: no artifacts downloaded; failing due to --fail-if-none-downloaded." in cp.stderr
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["download_retries"] == 1
    assert payload["download_retry_delay_sec"] == 1
    assert payload["downloaded_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["perf_report_count"] == 0
    assert payload["metric_report_count"] == 0
    assert payload["no_metric_report_count"] == 0
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["fail_if_none_downloaded"] is True
    assert payload["failed_due_to_zero_downloads"] is True
    assert payload["clean_download_dir"] is False
    assert payload["run_results"] == [{"run_id": "700", "downloaded": False, "attempts": 1}]


def test_strict_gate_perf_download_and_trend_fail_if_skipped(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([{"databaseId": 701, "status": "completed", "conclusion": "failure"}]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    # Simulate artifact not found for selected runs.
    raise SystemExit(1)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--fail-if-skipped",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 1, cp.stdout + "\n" + cp.stderr
    assert "Downloaded artifacts: 0" in cp.stdout
    assert "ERROR: skipped downloads detected; failing due to --fail-if-skipped." in cp.stderr
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["download_retries"] == 1
    assert payload["download_retry_delay_sec"] == 1
    assert payload["downloaded_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["perf_report_count"] == 0
    assert payload["metric_report_count"] == 0
    assert payload["no_metric_report_count"] == 0
    assert payload["fail_if_skipped"] is True
    assert payload["failed_due_to_skipped"] is True
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["fail_if_none_downloaded"] is False
    assert payload["failed_due_to_zero_downloads"] is False
    assert payload["clean_download_dir"] is False
    assert payload["run_results"] == [{"run_id": "701", "downloaded": False, "attempts": 1}]


def test_strict_gate_perf_download_and_trend_fail_if_no_runs(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    raise SystemExit(9)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--fail-if-no-runs",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 1, cp.stdout + "\n" + cp.stderr
    assert "Selected runs: 0" in cp.stdout
    assert "ERROR: no runs selected; failing due to --fail-if-no-runs." in cp.stderr
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["download_retries"] == 1
    assert payload["download_retry_delay_sec"] == 1
    assert payload["downloaded_count"] == 0
    assert payload["skipped_count"] == 0
    assert payload["perf_report_count"] == 0
    assert payload["metric_report_count"] == 0
    assert payload["no_metric_report_count"] == 0
    assert payload["selected_run_ids"] == []
    assert payload["downloaded_run_ids"] == []
    assert payload["skipped_run_ids"] == []
    assert payload["run_results"] == []
    assert payload["fail_if_no_runs"] is True
    assert payload["failed_due_to_no_runs"] is True
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_no_metrics"] is False
    assert payload["failed_due_to_no_metrics"] is False
    assert payload["fail_if_none_downloaded"] is False
    assert payload["failed_due_to_zero_downloads"] is False


def test_strict_gate_perf_download_and_trend_fail_if_no_metrics(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_perf_download_and_trend.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    print(json.dumps([{"databaseId": 702, "status": "completed", "conclusion": "success"}]))
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "download":
    run_id = args[2]
    out_dir = "."
    i = 3
    while i < len(args):
        if args[i] == "-D" and i + 1 < len(args):
            out_dir = args[i + 1]
            i += 2
            continue
        i += 1
    p = Path(out_dir) / "docs" / "DAILY_REPORTS"
    p.mkdir(parents=True, exist_ok=True)
    # Deliberately write a summary without metric table rows.
    report = "\\n".join(
        [
            "## Perf Smoke Summary",
            "",
            "- No perf metrics collected in this run.",
            "",
        ]
    )
    (p / f"STRICT_GATE_CI_{run_id}_PERF.md").write_text(report, encoding="utf-8")
    raise SystemExit(0)

raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    download_dir = tmp_path / "downloaded"
    trend_out = download_dir / "STRICT_GATE_PERF_TREND.md"
    json_out = download_dir / "strict_gate_perf_download.json"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--limit",
            "1",
            "--fail-if-no-metrics",
            "--download-dir",
            str(download_dir),
            "--trend-out",
            str(trend_out),
            "--json-out",
            str(json_out),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 1, cp.stdout + "\n" + cp.stderr
    assert "Selected runs: 1" in cp.stdout
    assert "Perf reports: 1 (with metrics: 0, no metrics: 1)" in cp.stdout
    assert "ERROR: selected runs contain no perf metrics; failing due to --fail-if-no-metrics." in cp.stderr
    assert trend_out.is_file(), f"Missing trend output: {trend_out}"
    assert json_out.is_file(), f"Missing json output: {json_out}"

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["max_run_age_days"] is None
    assert payload["download_retries"] == 1
    assert payload["download_retry_delay_sec"] == 1
    assert payload["downloaded_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["perf_report_count"] == 1
    assert payload["metric_report_count"] == 0
    assert payload["no_metric_report_count"] == 1
    assert payload["fail_if_no_runs"] is False
    assert payload["failed_due_to_no_runs"] is False
    assert payload["fail_if_skipped"] is False
    assert payload["failed_due_to_skipped"] is False
    assert payload["fail_if_none_downloaded"] is False
    assert payload["failed_due_to_zero_downloads"] is False
    assert payload["fail_if_no_metrics"] is True
    assert payload["failed_due_to_no_metrics"] is True
