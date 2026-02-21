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


def test_recent_perf_audit_regression_script_runs_with_fake_gh_and_writes_summaries(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_recent_perf_audit_regression.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_state = tmp_path / "fake_gh_run_list_count.txt"
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

INVALID_RUN_ID = "9101"
VALID_RUN_ID = "9201"

args = sys.argv[1:]
state_file = Path(os.environ["FAKE_GH_STATE"])

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

def next_run_list_count() -> int:
    count = 0
    if state_file.exists():
        count = int(state_file.read_text(encoding="utf-8").strip() or "0")
    count += 1
    state_file.write_text(str(count), encoding="utf-8")
    return count

def print_jobs(run_id: str) -> None:
    if run_id == INVALID_RUN_ID:
        validate = "failure"
        optional = "skipped"
        upload = "skipped"
    else:
        validate = "success"
        optional = "success"
        upload = "success"
    payload = {
        "jobs": [
            {
                "steps": [
                    {"name": "Validate recent perf audit inputs", "conclusion": validate},
                    {"name": "Optional recent perf audit (download + trend)", "conclusion": optional},
                    {"name": "Upload strict gate recent perf audit", "conclusion": upload},
                ]
            }
        ]
    }
    print(json.dumps(payload))

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "workflow" and args[1] == "run":
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    count = next_run_list_count()
    if count == 1:
        print("9001")
        print("9002")
    elif count == 2:
        print("9001")
        print("9002")
        print(INVALID_RUN_ID)
    elif count == 3:
        print("9001")
        print("9002")
        print(INVALID_RUN_ID)
    else:
        print("9001")
        print("9002")
        print(INVALID_RUN_ID)
        print(VALID_RUN_ID)
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "view":
    run_id = args[2]
    if "--log-failed" in args:
        if run_id == INVALID_RUN_ID:
            print("ERROR: recent_perf_audit_limit must be <= 100 (got: 101)")
        raise SystemExit(0)

    if "--json" in args:
        json_key = args[args.index("--json") + 1]
        jq_expr = ""
        if "--jq" in args:
            jq_expr = args[args.index("--jq") + 1]

        if json_key == "status" and jq_expr == ".status":
            print("completed")
            raise SystemExit(0)
        if json_key == "conclusion" and jq_expr == ".conclusion":
            print("failure" if run_id == INVALID_RUN_ID else "success")
            raise SystemExit(0)
        if json_key == "url" and jq_expr == ".url":
            print(f"https://example.invalid/runs/{run_id}")
            raise SystemExit(0)
        if json_key == "jobs":
            print_jobs(run_id)
            raise SystemExit(0)

if len(args) >= 1 and args[0] == "api":
    endpoint = args[1] if len(args) > 1 else ""
    m = re.search(r"/actions/runs/(\\d+)/artifacts", endpoint)
    if not m:
        raise SystemExit(2)
    run_id = m.group(1)
    if run_id == VALID_RUN_ID:
        print("strict-gate-report")
        print("strict-gate-perf-summary")
        print("strict-gate-perf-trend")
        print("strict-gate-logs")
        print("strict-gate-recent-perf-audit")
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

    if run_id != VALID_RUN_ID or artifact_name != "strict-gate-recent-perf-audit":
        raise SystemExit(1)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    payload = {
        "conclusion": "success",
        "max_run_age_days": 1,
        "fail_if_no_metrics": False,
        "downloaded_count": 3,
    }
    (out_path / "strict_gate_perf_download.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    out_dir = tmp_path / "out"
    summary_json = out_dir / "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json"
    summary_md = out_dir / "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md"

    env = os.environ.copy()
    env["FAKE_GH_STATE"] = str(fake_state)
    # Keep PATH minimal to force script fallback branch when `rg` is unavailable.
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--repo",
            "fake-org/fake-repo",
            "--ref",
            "main",
            "--poll-interval-sec",
            "1",
            "--max-wait-sec",
            "30",
            "--out-dir",
            str(out_dir),
            "--summary-json",
            str(summary_json),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert summary_md.is_file(), f"Missing markdown summary: {summary_md}"
    assert summary_json.is_file(), f"Missing json summary: {summary_json}"

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["result"] == "success"
    assert payload["failure_reason"] == ""
    assert payload["invalid_case"]["run_id"] == "9101"
    assert payload["invalid_case"]["conclusion"] == "failure"
    assert payload["invalid_case"]["artifact_count"] == 0
    assert payload["valid_case"]["run_id"] == "9201"
    assert payload["valid_case"]["conclusion"] == "success"
    assert payload["valid_case"]["requested_fail_if_no_metrics"] is False
    assert payload["valid_case"]["artifacts"] == [
        "strict-gate-report",
        "strict-gate-perf-summary",
        "strict-gate-perf-trend",
        "strict-gate-logs",
        "strict-gate-recent-perf-audit",
    ]

    md_text = summary_md.read_text(encoding="utf-8", errors="replace")
    assert "result: success" in md_text
    assert "failure_reason: none" in md_text
    assert "run_id: 9101" in md_text
    assert "artifact_count: 0" in md_text
    assert "run_id: 9201" in md_text
    assert "- strict-gate-recent-perf-audit" in md_text


def test_recent_perf_audit_regression_script_writes_summary_on_failure(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "strict_gate_recent_perf_audit_regression.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_state = tmp_path / "fake_gh_run_list_count.txt"
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

INVALID_RUN_ID = "9101"
VALID_RUN_ID = "9201"

args = sys.argv[1:]
state_file = Path(os.environ["FAKE_GH_STATE"])

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

def next_run_list_count() -> int:
    count = 0
    if state_file.exists():
        count = int(state_file.read_text(encoding="utf-8").strip() or "0")
    count += 1
    state_file.write_text(str(count), encoding="utf-8")
    return count

def print_jobs(run_id: str) -> None:
    if run_id == INVALID_RUN_ID:
        validate = "failure"
        optional = "skipped"
        upload = "skipped"
    else:
        validate = "success"
        optional = "failure"
        upload = "skipped"
    payload = {
        "jobs": [
            {
                "steps": [
                    {"name": "Validate recent perf audit inputs", "conclusion": validate},
                    {"name": "Optional recent perf audit (download + trend)", "conclusion": optional},
                    {"name": "Upload strict gate recent perf audit", "conclusion": upload},
                ]
            }
        ]
    }
    print(json.dumps(payload))

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "workflow" and args[1] == "run":
    raise SystemExit(0)

if len(args) >= 2 and args[0] == "run" and args[1] == "list":
    count = next_run_list_count()
    if count == 1:
        print("9001")
        print("9002")
    elif count == 2:
        print("9001")
        print("9002")
        print(INVALID_RUN_ID)
    elif count == 3:
        print("9001")
        print("9002")
        print(INVALID_RUN_ID)
    else:
        print("9001")
        print("9002")
        print(INVALID_RUN_ID)
        print(VALID_RUN_ID)
    raise SystemExit(0)

if len(args) >= 3 and args[0] == "run" and args[1] == "view":
    run_id = args[2]
    if "--log-failed" in args:
        if run_id == INVALID_RUN_ID:
            print("ERROR: recent_perf_audit_limit must be <= 100 (got: 101)")
        raise SystemExit(0)

    if "--json" in args:
        json_key = args[args.index("--json") + 1]
        jq_expr = ""
        if "--jq" in args:
            jq_expr = args[args.index("--jq") + 1]

        if json_key == "status" and jq_expr == ".status":
            print("completed")
            raise SystemExit(0)
        if json_key == "conclusion" and jq_expr == ".conclusion":
            print("failure")
            raise SystemExit(0)
        if json_key == "url" and jq_expr == ".url":
            print(f"https://example.invalid/runs/{run_id}")
            raise SystemExit(0)
        if json_key == "jobs":
            print_jobs(run_id)
            raise SystemExit(0)

if len(args) >= 1 and args[0] == "api":
    endpoint = args[1] if len(args) > 1 else ""
    m = re.search(r"/actions/runs/(\\d+)/artifacts", endpoint)
    if not m:
        raise SystemExit(2)
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    out_dir = tmp_path / "out"
    summary_json = out_dir / "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.json"
    summary_md = out_dir / "STRICT_GATE_RECENT_PERF_AUDIT_REGRESSION.md"

    env = os.environ.copy()
    env["FAKE_GH_STATE"] = str(fake_state)
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--repo",
            "fake-org/fake-repo",
            "--ref",
            "main",
            "--poll-interval-sec",
            "1",
            "--max-wait-sec",
            "30",
            "--out-dir",
            str(out_dir),
            "--summary-json",
            str(summary_json),
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )
    assert cp.returncode != 0, cp.stdout + "\n" + cp.stderr
    assert summary_md.is_file(), f"Missing markdown summary on failure: {summary_md}"
    assert summary_json.is_file(), f"Missing json summary on failure: {summary_json}"

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["result"] == "failure"
    assert "valid case run conclusion expected 'success' but got 'failure'" in payload["failure_reason"]
    assert payload["valid_case"]["run_id"] == "9201"
    assert payload["valid_case"]["conclusion"] == "failure"

    md_text = summary_md.read_text(encoding="utf-8", errors="replace")
    assert "result: failure" in md_text
    assert "run_id: 9201" in md_text
