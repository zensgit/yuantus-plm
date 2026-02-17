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
    assert payload["artifact_name"] == "strict-gate-perf-summary"
    assert payload["downloaded_count"] == 2
    assert payload["skipped_count"] == 0
    assert payload["run_id_mode"] is False
    assert payload["fail_if_none_downloaded"] is False
    assert payload["failed_due_to_zero_downloads"] is False
    assert payload["selected_run_ids"] == ["101", "100"]
    assert payload["downloaded_run_ids"] == ["101", "100"]
    assert payload["skipped_run_ids"] == []


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
    assert payload["artifact_name"] == "custom-perf-artifact"
    assert payload["downloaded_count"] == 1
    assert payload["skipped_count"] == 0
    assert payload["fail_if_none_downloaded"] is False
    assert payload["failed_due_to_zero_downloads"] is False
    assert payload["selected_run_ids"] == ["501"]
    assert payload["downloaded_run_ids"] == ["501"]


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
    out = trend_out.read_text(encoding="utf-8", errors="replace")
    assert "`STRICT_GATE_CI_888`" in out


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
    assert payload["downloaded_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["fail_if_none_downloaded"] is True
    assert payload["failed_due_to_zero_downloads"] is True
