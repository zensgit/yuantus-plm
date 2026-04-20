from __future__ import annotations

import json
import os
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


def _write_fake_python_proxy(path: Path, *, compare_exit: int | None = None, evaluate_exit: int | None = None) -> None:
    path.write_text(
        f"""#!{sys.executable}
import subprocess
import sys
from pathlib import Path

real_python = {sys.executable!r}
compare_exit = {compare_exit!r}
evaluate_exit = {evaluate_exit!r}
target = Path(sys.argv[1]).name if len(sys.argv) > 1 else ""

if target == "compare_p2_observation_results.py" and compare_exit is not None:
    print("synthetic compare failure", file=sys.stderr)
    raise SystemExit(compare_exit)

if target == "evaluate_p2_observation_results.py" and evaluate_exit is not None:
    print("synthetic evaluate failure", file=sys.stderr)
    raise SystemExit(evaluate_exit)

cp = subprocess.run([real_python, *sys.argv[1:]], check=False)
raise SystemExit(cp.returncode)
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_p2_observation_regression_workflow_wrapper_with_fake_gh(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_observation_regression_workflow.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    dispatch_log = tmp_path / "dispatch_args.json"
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if args[:2] == ["repo", "view"]:
    print("zensgit/yuantus-plm")
    raise SystemExit(0)

if args[:2] == ["workflow", "run"]:
    Path(os.environ["FAKE_GH_DISPATCH_LOG"]).write_text(
        json.dumps(args, ensure_ascii=True),
        encoding="utf-8",
    )
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    print(json.dumps([
        {
            "databaseId": 101,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2020-01-01T00:00:00Z",
        },
        {
            "databaseId": 202,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2099-01-01T00:00:00Z",
        },
    ]))
    raise SystemExit(0)

if args[:3] == ["run", "watch", "202"]:
    raise SystemExit(0)

if args[:3] == ["run", "view", "202"] and "--json" in args and "--jq" in args:
    json_key = args[args.index("--json") + 1]
    jq_expr = args[args.index("--jq") + 1]
    if json_key == "status" and jq_expr == ".status":
        print("completed")
        raise SystemExit(0)
    if json_key == "conclusion" and jq_expr == ".conclusion":
        print("success")
        raise SystemExit(0)
    if json_key == "url" and jq_expr == ".url":
        print("https://example.invalid/runs/202")
        raise SystemExit(0)

if args[:3] == ["run", "download", "202"]:
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
    if artifact_name != "p2-observation-regression":
        raise SystemExit(1)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "OBSERVATION_RESULT.md").write_text("# result\\n", encoding="utf-8")
    (out_path / "OBSERVATION_EVAL.md").write_text("# eval\\n", encoding="utf-8")
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    out_dir = tmp_path / "out"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    env["FAKE_GH_DISPATCH_LOG"] = str(dispatch_log)

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--base-url",
            "https://dev.example.invalid/",
            "--tenant-id",
            "tenant-1",
            "--org-id",
            "org-1",
            "--username",
            "admin",
            "--environment",
            "shared-dev",
            "--eco-type",
            "ECR",
            "--out-dir",
            str(out_dir),
            "--poll-interval-sec",
            "1",
            "--max-discovery-sec",
            "5",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "run_id=202" in cp.stdout
    assert (out_dir / "WORKFLOW_DISPATCH_RESULT.md").is_file()
    assert (out_dir / "workflow_dispatch.json").is_file()
    assert (out_dir / "artifact" / "OBSERVATION_RESULT.md").is_file()
    assert (out_dir / "artifact" / "OBSERVATION_EVAL.md").is_file()

    payload = json.loads((out_dir / "workflow_dispatch.json").read_text(encoding="utf-8"))
    assert payload["result"] == "success"
    assert payload["repo"] == "zensgit/yuantus-plm"
    assert payload["base_url"] == "https://dev.example.invalid"
    assert payload["run_id"] == "202"
    assert payload["run_conclusion"] == "success"
    assert payload["run_url"] == "https://example.invalid/runs/202"
    assert payload["eco_type"] == "ECR"

    dispatch_args = json.loads(dispatch_log.read_text(encoding="utf-8"))
    assert dispatch_args[:2] == ["workflow", "run"]
    assert "--field" in dispatch_args
    assert "base_url=https://dev.example.invalid" in dispatch_args
    assert "tenant_id=tenant-1" in dispatch_args
    assert "org_id=org-1" in dispatch_args
    assert "environment=shared-dev" in dispatch_args
    assert "eco_type=ECR" in dispatch_args


def test_p2_observation_regression_workflow_wrapper_writes_summary_on_discovery_failure(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_observation_regression_workflow.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import sys

args = sys.argv[1:]

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if args[:2] == ["repo", "view"]:
    print("zensgit/yuantus-plm")
    raise SystemExit(0)

if args[:2] == ["workflow", "run"]:
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    print(json.dumps([
        {
            "databaseId": 101,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2020-01-01T00:00:00Z",
        }
    ]))
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    out_dir = tmp_path / "out-fail"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--base-url",
            "https://dev.example.invalid",
            "--out-dir",
            str(out_dir),
            "--poll-interval-sec",
            "1",
            "--max-discovery-sec",
            "1",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )

    assert cp.returncode != 0
    assert "failed to discover workflow run id" in (cp.stderr or "")
    assert (out_dir / "WORKFLOW_DISPATCH_RESULT.md").is_file()
    assert (out_dir / "workflow_dispatch.json").is_file()

    payload = json.loads((out_dir / "workflow_dispatch.json").read_text(encoding="utf-8"))
    assert payload["result"] == "failure"
    assert "failed to discover workflow run id" in payload["failure_reason"]

    md_text = (out_dir / "WORKFLOW_DISPATCH_RESULT.md").read_text(encoding="utf-8")
    assert "result: failure" in md_text
    assert "failed to discover workflow run id" in md_text


def test_p2_observation_regression_workflow_wrapper_surfaces_precheck_failure_reason(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_observation_regression_workflow.sh"
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

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if args[:2] == ["repo", "view"]:
    print("zensgit/yuantus-plm")
    raise SystemExit(0)

if args[:2] == ["workflow", "run"]:
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    print(json.dumps([
        {
            "databaseId": 909,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2099-01-01T00:00:00Z",
        }
    ]))
    raise SystemExit(0)

if args[:3] == ["run", "watch", "909"]:
    raise SystemExit(1)

if args[:3] == ["run", "view", "909"] and "--json" in args and "--jq" in args:
    json_key = args[args.index("--json") + 1]
    jq_expr = args[args.index("--jq") + 1]
    if json_key == "status" and jq_expr == ".status":
        print("completed")
        raise SystemExit(0)
    if json_key == "conclusion" and jq_expr == ".conclusion":
        print("failure")
        raise SystemExit(0)
    if json_key == "url" and jq_expr == ".url":
        print("https://example.invalid/runs/909")
        raise SystemExit(0)

if args[:3] == ["run", "download", "909"]:
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
    if artifact_name != "p2-observation-regression":
        raise SystemExit(1)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "WORKFLOW_PRECHECK.md").write_text("# precheck\\n", encoding="utf-8")
    (out_path / "workflow_precheck.json").write_text(
        json.dumps(
            {
                "result": "failure",
                "reason": "missing authentication secret",
                "required": ["P2_OBSERVATION_TOKEN", "P2_OBSERVATION_PASSWORD"],
            }
        ) + "\\n",
        encoding="utf-8",
    )
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    out_dir = tmp_path / "out-precheck-failure"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--base-url",
            "https://dev.example.invalid",
            "--out-dir",
            str(out_dir),
            "--poll-interval-sec",
            "1",
            "--max-discovery-sec",
            "5",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )

    assert cp.returncode != 0
    assert "missing authentication secret" in (cp.stderr or "")
    assert "P2_OBSERVATION_TOKEN" in (cp.stderr or "")
    assert (out_dir / "workflow_dispatch.json").is_file()
    assert (out_dir / "WORKFLOW_DISPATCH_RESULT.md").is_file()
    assert (out_dir / "artifact" / "workflow_precheck.json").is_file()

    payload = json.loads((out_dir / "workflow_dispatch.json").read_text(encoding="utf-8"))
    assert payload["result"] == "failure"
    assert "missing authentication secret" in payload["failure_reason"]
    assert "P2_OBSERVATION_TOKEN" in payload["failure_reason"]

    md_text = (out_dir / "WORKFLOW_DISPATCH_RESULT.md").read_text(encoding="utf-8")
    assert "missing authentication secret" in md_text
    assert "P2_OBSERVATION_TOKEN" in md_text


def test_p2_shared_dev_142_workflow_probe_wrapper_uses_fixed_defaults(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_shared_dev_142_workflow_probe.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    dispatch_log = tmp_path / "dispatch_args.json"
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if args[:2] == ["repo", "view"]:
    print("zensgit/yuantus-plm")
    raise SystemExit(0)

if args[:2] == ["workflow", "run"]:
    Path(os.environ["FAKE_GH_DISPATCH_LOG"]).write_text(
        json.dumps(args, ensure_ascii=True),
        encoding="utf-8",
    )
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    print(json.dumps([
        {
            "databaseId": 303,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2099-01-01T00:00:00Z",
        },
    ]))
    raise SystemExit(0)

if args[:3] == ["run", "watch", "303"]:
    raise SystemExit(0)

if args[:3] == ["run", "view", "303"] and "--json" in args and "--jq" in args:
    json_key = args[args.index("--json") + 1]
    jq_expr = args[args.index("--jq") + 1]
    if json_key == "status" and jq_expr == ".status":
        print("completed")
        raise SystemExit(0)
    if json_key == "conclusion" and jq_expr == ".conclusion":
        print("success")
        raise SystemExit(0)
    if json_key == "url" and jq_expr == ".url":
        print("https://example.invalid/runs/303")
        raise SystemExit(0)

if args[:3] == ["run", "download", "303"]:
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
    if artifact_name != "p2-observation-regression":
        raise SystemExit(1)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "OBSERVATION_RESULT.md").write_text("# result\\n", encoding="utf-8")
    (out_path / "OBSERVATION_EVAL.md").write_text("# eval\\n", encoding="utf-8")
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    out_dir = tmp_path / "out-142"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    env["FAKE_GH_DISPATCH_LOG"] = str(dispatch_log)

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--out-dir",
            str(out_dir),
            "--eco-state",
            "open",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "BASE_URL=http://142.171.239.56:7910" in cp.stdout
    assert "NOTE=current-only workflow probe" in cp.stdout
    assert (out_dir / "WORKFLOW_DISPATCH_RESULT.md").is_file()
    assert (out_dir / "workflow_dispatch.json").is_file()

    payload = json.loads((out_dir / "workflow_dispatch.json").read_text(encoding="utf-8"))
    assert payload["result"] == "success"
    assert payload["base_url"] == "http://142.171.239.56:7910"
    assert payload["environment"] == "shared-dev-142-workflow-probe"
    assert payload["eco_state"] == "open"

    dispatch_args = json.loads(dispatch_log.read_text(encoding="utf-8"))
    assert "base_url=http://142.171.239.56:7910" in dispatch_args
    assert "tenant_id=tenant-1" in dispatch_args
    assert "org_id=org-1" in dispatch_args
    assert "environment=shared-dev-142-workflow-probe" in dispatch_args
    assert "eco_state=open" in dispatch_args


def test_p2_shared_dev_142_entrypoint_wrapper_dry_run_routes_modes(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_shared_dev_142_entrypoint.sh"
    assert script.is_file(), f"Missing script: {script}"

    def _run(mode: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [
                "bash",
                str(script),
                "--mode",
                mode,
                "--dry-run",
                "--",
                *args,
            ],
            text=True,
            capture_output=True,
            cwd=str(repo_root),
        )

    probe = _run("workflow-probe", "--eco-state", "open")
    assert probe.returncode == 0, probe.stdout + "\n" + probe.stderr
    assert "MODE=workflow-probe" in probe.stdout
    assert "TARGET=scripts/run_p2_shared_dev_142_workflow_probe.sh" in probe.stdout
    assert "FORWARDED_ARGS=--eco-state open " in probe.stdout
    assert "DRY_RUN=1" in probe.stdout

    readonly = _run("readonly-rerun", "--skip-precheck")
    assert readonly.returncode == 0, readonly.stdout + "\n" + readonly.stderr
    assert "MODE=readonly-rerun" in readonly.stdout
    assert "TARGET=scripts/run_p2_shared_dev_142_readonly_rerun.sh" in readonly.stdout
    assert "DRY_RUN=1" in readonly.stdout

    drift_audit = _run("drift-audit", "--skip-precheck")
    assert drift_audit.returncode == 0, drift_audit.stdout + "\n" + drift_audit.stderr
    assert "MODE=drift-audit" in drift_audit.stdout
    assert "TARGET=scripts/run_p2_shared_dev_142_drift_audit.sh" in drift_audit.stdout
    assert "DRY_RUN=1" in drift_audit.stdout

    drift_investigation = _run("drift-investigation", "--skip-precheck")
    assert drift_investigation.returncode == 0, drift_investigation.stdout + "\n" + drift_investigation.stderr
    assert "MODE=drift-investigation" in drift_investigation.stdout
    assert "TARGET=scripts/run_p2_shared_dev_142_drift_investigation.sh" in drift_investigation.stdout
    assert "DRY_RUN=1" in drift_investigation.stdout

    workflow_readonly = _run("workflow-readonly-check", "--eco-type", "ECR")
    assert workflow_readonly.returncode == 0, workflow_readonly.stdout + "\n" + workflow_readonly.stderr
    assert "MODE=workflow-readonly-check" in workflow_readonly.stdout
    assert "TARGET=scripts/run_p2_shared_dev_142_workflow_readonly_check.sh" in workflow_readonly.stdout
    assert "FORWARDED_ARGS=--eco-type ECR " in workflow_readonly.stdout
    assert "DRY_RUN=1" in workflow_readonly.stdout

    print_mode = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--mode",
            "print-readonly-commands",
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert print_mode.returncode == 0, print_mode.stdout + "\n" + print_mode.stderr
    assert "MODE=print-readonly-commands" in print_mode.stdout
    assert "TARGET=scripts/print_p2_shared_dev_142_readonly_rerun_commands.sh" in print_mode.stdout
    assert "FORWARDED_ARGS=<none>" in print_mode.stdout
    assert "DRY_RUN=1" in print_mode.stdout

    print_drift_mode = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--mode",
            "print-drift-commands",
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert print_drift_mode.returncode == 0, print_drift_mode.stdout + "\n" + print_drift_mode.stderr
    assert "MODE=print-drift-commands" in print_drift_mode.stdout
    assert "TARGET=scripts/print_p2_shared_dev_142_drift_audit_commands.sh" in print_drift_mode.stdout
    assert "FORWARDED_ARGS=<none>" in print_drift_mode.stdout
    assert "DRY_RUN=1" in print_drift_mode.stdout

    print_investigation_mode = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--mode",
            "print-investigation-commands",
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert print_investigation_mode.returncode == 0, print_investigation_mode.stdout + "\n" + print_investigation_mode.stderr
    assert "MODE=print-investigation-commands" in print_investigation_mode.stdout
    assert "TARGET=scripts/print_p2_shared_dev_142_drift_investigation_commands.sh" in print_investigation_mode.stdout
    assert "FORWARDED_ARGS=<none>" in print_investigation_mode.stdout
    assert "DRY_RUN=1" in print_investigation_mode.stdout


def test_render_p2_shared_dev_142_drift_audit_summarizes_metric_and_item_drift(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "render_p2_shared_dev_142_drift_audit.py"
    assert script.is_file(), f"Missing script: {script}"

    baseline_dir = tmp_path / "baseline"
    current_dir = tmp_path / "current"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    current_dir.mkdir(parents=True, exist_ok=True)

    (baseline_dir / "summary.json").write_text(
        json.dumps({"pending_count": 2, "overdue_count": 3, "escalated_count": 1}) + "\n",
        encoding="utf-8",
    )
    (current_dir / "summary.json").write_text(
        json.dumps({"pending_count": 1, "overdue_count": 4, "escalated_count": 1}) + "\n",
        encoding="utf-8",
    )

    (baseline_dir / "items.json").write_text(
        json.dumps(
            [
                {"approval_id": "a-1", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-2", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-3", "is_overdue": True, "is_escalated": False},
                {"approval_id": "a-4", "is_overdue": True, "is_escalated": True},
                {"approval_id": "a-5", "is_overdue": True, "is_escalated": False},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (current_dir / "items.json").write_text(
        json.dumps(
            [
                {"approval_id": "a-1", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-3", "is_overdue": True, "is_escalated": False},
                {"approval_id": "a-4", "is_overdue": True, "is_escalated": True},
                {"approval_id": "a-5", "is_overdue": True, "is_escalated": False},
                {"approval_id": "a-6", "is_overdue": True, "is_escalated": False},
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    (baseline_dir / "anomalies.json").write_text(
        json.dumps(
            {
                "total_anomalies": 2,
                "no_candidates": [],
                "escalated_unresolved": [{"approval_id": "a-4"}],
                "overdue_not_escalated": [{"approval_id": "a-3"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (current_dir / "anomalies.json").write_text(
        json.dumps(
            {
                "total_anomalies": 3,
                "no_candidates": [],
                "escalated_unresolved": [{"approval_id": "a-4"}],
                "overdue_not_escalated": [{"approval_id": "a-3"}, {"approval_id": "a-6"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    (baseline_dir / "export.json").write_text(
        json.dumps([{"approval_id": f"a-{n}"} for n in range(1, 6)]) + "\n",
        encoding="utf-8",
    )
    (current_dir / "export.json").write_text(
        json.dumps([{"approval_id": "a-1"}, {"approval_id": "a-3"}, {"approval_id": "a-4"}, {"approval_id": "a-5"}, {"approval_id": "a-6"}]) + "\n",
        encoding="utf-8",
    )

    (baseline_dir / "export.csv").write_text(
        "approval_id\na-1\na-2\na-3\na-4\na-5\n",
        encoding="utf-8",
    )
    (current_dir / "export.csv").write_text(
        "approval_id\na-1\na-3\na-4\na-5\na-6\n",
        encoding="utf-8",
    )

    md_path = current_dir / "DRIFT_AUDIT.md"
    json_path = current_dir / "drift_audit.json"
    cp = subprocess.run(  # noqa: S603
        [
            "python3",
            str(script),
            str(baseline_dir),
            str(current_dir),
            "--baseline-label",
            "shared-dev-142-readonly-20260419",
            "--current-label",
            "current-drift-audit",
            "--output-md",
            str(md_path),
            "--output-json",
            str(json_path),
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert md_path.is_file()
    assert json_path.is_file()

    md_text = md_path.read_text(encoding="utf-8")
    assert "verdict：FAIL" in md_text
    assert "`pending_count`" in md_text
    assert "`2` | `1` | `-1`" in md_text
    assert "`overdue_count`" in md_text
    assert "`3` | `4` | `1`" in md_text
    assert "`a-6`" in md_text
    assert "`a-2`" in md_text

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["verdict"] == "FAIL"
    assert payload["added_approval_ids"] == ["a-6"]
    assert payload["removed_approval_ids"] == ["a-2"]


def test_render_p2_shared_dev_142_drift_investigation_summarizes_classification_and_evidence(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "render_p2_shared_dev_142_drift_investigation.py"
    assert script.is_file(), f"Missing script: {script}"

    drift_dir = tmp_path / "drift-audit"
    drift_dir.mkdir(parents=True, exist_ok=True)
    (drift_dir / "drift_audit.json").write_text(
        json.dumps(
            {
                "verdict": "FAIL",
                "metric_deltas": {
                    "pending_count": {"baseline": 2, "current": 1, "delta": -1},
                    "overdue_count": {"baseline": 3, "current": 4, "delta": 1},
                    "total_anomalies": {"baseline": 2, "current": 3, "delta": 1},
                },
                "added_approval_ids": [],
                "removed_approval_ids": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    md_path = tmp_path / "DRIFT_INVESTIGATION.md"
    json_path = tmp_path / "drift_investigation.json"
    cp = subprocess.run(  # noqa: S603
        [
            "python3",
            str(script),
            str(drift_dir),
            "--output-md",
            str(md_path),
            "--output-json",
            str(json_path),
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert md_path.is_file()
    assert json_path.is_file()

    md_text = md_path.read_text(encoding="utf-8")
    assert "classification：state-drift" in md_text
    assert "src/yuantus/meta_engine/web/eco_router.py" in md_text
    assert "drift-audit/current/OBSERVATION_RESULT.md" in md_text
    assert "drift-audit/drift_audit.json" in md_text

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["classification"] == "state-drift"
    assert any(
        entry["path"] == "src/yuantus/meta_engine/web/eco_router.py"
        for entry in payload["candidate_write_sources"]
    )
    assert "result_markdown" in payload["evidence_paths"]


def test_run_p2_shared_dev_142_drift_audit_still_renders_when_readonly_rerun_fails(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    temp_repo = tmp_path / "repo"
    scripts_dir = temp_repo / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    drift_runner = repo_root / "scripts" / "run_p2_shared_dev_142_drift_audit.sh"
    drift_renderer = repo_root / "scripts" / "render_p2_shared_dev_142_drift_audit.py"
    assert drift_runner.is_file(), f"Missing script: {drift_runner}"
    assert drift_renderer.is_file(), f"Missing script: {drift_renderer}"

    (scripts_dir / "run_p2_shared_dev_142_drift_audit.sh").write_text(
        drift_runner.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts_dir / "run_p2_shared_dev_142_drift_audit.sh").chmod(0o755)
    (scripts_dir / "render_p2_shared_dev_142_drift_audit.py").write_text(
        drift_renderer.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts_dir / "render_p2_shared_dev_142_drift_audit.py").chmod(0o755)

    stub_readonly = scripts_dir / "run_p2_shared_dev_142_readonly_rerun.sh"
    stub_readonly.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

output_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      output_dir="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

mkdir -p "${output_dir}" "${output_dir}-precheck"
printf '%s\\n' '{"pending_count":1,"overdue_count":4,"escalated_count":1}' > "${output_dir}/summary.json"
printf '%s\\n' '[{"approval_id":"a-1","is_overdue":false,"is_escalated":false},{"approval_id":"a-3","is_overdue":true,"is_escalated":false},{"approval_id":"a-4","is_overdue":true,"is_escalated":true},{"approval_id":"a-5","is_overdue":true,"is_escalated":false},{"approval_id":"a-6","is_overdue":true,"is_escalated":false}]' > "${output_dir}/items.json"
printf '%s\\n' '{"total_anomalies":3,"no_candidates":[],"escalated_unresolved":[{"approval_id":"a-4"}],"overdue_not_escalated":[{"approval_id":"a-3"},{"approval_id":"a-6"}]}' > "${output_dir}/anomalies.json"
printf '%s\\n' '[{"approval_id":"a-1"},{"approval_id":"a-3"},{"approval_id":"a-4"},{"approval_id":"a-5"},{"approval_id":"a-6"}]' > "${output_dir}/export.json"
cat <<'EOF' > "${output_dir}/export.csv"
approval_id
a-1
a-3
a-4
a-5
a-6
EOF
printf '%s\\n' '# result' > "${output_dir}/OBSERVATION_RESULT.md"
printf '%s\\n' '# diff' > "${output_dir}/OBSERVATION_DIFF.md"
printf '%s\\n' '# eval' > "${output_dir}/OBSERVATION_EVAL.md"
printf '%s\\n' '# precheck' > "${output_dir}-precheck/OBSERVATION_PRECHECK.md"
printf '%s\\n' '{"status":"ok"}' > "${output_dir}-precheck/observation_precheck.json"
printf '%s\\n' '{"http_status":200}' > "${output_dir}-precheck/summary_probe.json"
exit 1
""",
        encoding="utf-8",
    )
    stub_readonly.chmod(0o755)

    baseline_dir = temp_repo / "tmp" / "p2-shared-dev-observation-20260419-193242"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    (baseline_dir / "summary.json").write_text(
        json.dumps({"pending_count": 2, "overdue_count": 3, "escalated_count": 1}) + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "items.json").write_text(
        json.dumps(
            [
                {"approval_id": "a-1", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-2", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-3", "is_overdue": True, "is_escalated": False},
                {"approval_id": "a-4", "is_overdue": True, "is_escalated": True},
                {"approval_id": "a-5", "is_overdue": True, "is_escalated": False},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "anomalies.json").write_text(
        json.dumps(
            {
                "total_anomalies": 2,
                "no_candidates": [],
                "escalated_unresolved": [{"approval_id": "a-4"}],
                "overdue_not_escalated": [{"approval_id": "a-3"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "export.json").write_text(
        json.dumps([{"approval_id": f"a-{n}"} for n in range(1, 6)]) + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "export.csv").write_text(
        "approval_id\na-1\na-2\na-3\na-4\na-5\n",
        encoding="utf-8",
    )

    output_dir = temp_repo / "tmp" / "drift-audit"
    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(scripts_dir / "run_p2_shared_dev_142_drift_audit.sh"),
            "--env-file",
            str(temp_repo / "fake.env"),
            "--output-dir",
            str(output_dir),
            "--baseline-dir",
            str(baseline_dir),
            "--skip-precheck",
            "--no-archive",
        ],
        text=True,
        capture_output=True,
        cwd=str(temp_repo),
    )

    assert cp.returncode == 1, cp.stdout + "\n" + cp.stderr
    assert "Readonly rerun exited with status 1; continuing to render top-level drift audit." in cp.stderr
    assert "READONLY_EXIT_STATUS=1" in cp.stdout
    assert "DRIFT_VERDICT=FAIL" in cp.stdout
    assert (output_dir / "DRIFT_AUDIT.md").is_file()
    assert (output_dir / "drift_audit.json").is_file()

    payload = json.loads((output_dir / "drift_audit.json").read_text(encoding="utf-8"))
    assert payload["verdict"] == "FAIL"
    assert payload["added_approval_ids"] == ["a-6"]
    assert payload["removed_approval_ids"] == ["a-2"]


def test_p2_shared_dev_142_entrypoint_wrapper_rejects_invalid_mode(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_shared_dev_142_entrypoint.sh"
    assert script.is_file(), f"Missing script: {script}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--mode",
            "bad-mode",
            "--dry-run",
        ],
        text=True,
        capture_output=True,
        cwd=str(repo_root),
    )
    assert cp.returncode != 0
    assert "Unsupported --mode: bad-mode" in (cp.stderr or "")


def test_p2_shared_dev_142_workflow_readonly_check_wrapper_runs_probe_then_compare(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_shared_dev_142_workflow_readonly_check.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    dispatch_log = tmp_path / "dispatch_args.json"
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if args[:2] == ["repo", "view"]:
    print("zensgit/yuantus-plm")
    raise SystemExit(0)

if args[:2] == ["workflow", "run"]:
    Path(os.environ["FAKE_GH_DISPATCH_LOG"]).write_text(
        json.dumps(args, ensure_ascii=True),
        encoding="utf-8",
    )
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    print(json.dumps([
        {
            "databaseId": 404,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2099-01-01T00:00:00Z",
        },
    ]))
    raise SystemExit(0)

if args[:3] == ["run", "watch", "404"]:
    raise SystemExit(0)

if args[:3] == ["run", "view", "404"] and "--json" in args and "--jq" in args:
    json_key = args[args.index("--json") + 1]
    jq_expr = args[args.index("--jq") + 1]
    if json_key == "status" and jq_expr == ".status":
        print("completed")
        raise SystemExit(0)
    if json_key == "conclusion" and jq_expr == ".conclusion":
        print("success")
        raise SystemExit(0)
    if json_key == "url" and jq_expr == ".url":
        print("https://example.invalid/runs/404")
        raise SystemExit(0)

if args[:3] == ["run", "download", "404"]:
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
    if artifact_name != "p2-observation-regression":
        raise SystemExit(1)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    summary = {
        "pending_count": 2,
        "overdue_count": 3,
        "escalated_count": 1,
    }
    items = [
        {"approval_id": "a-1", "is_overdue": False, "is_escalated": False},
        {"approval_id": "a-2", "is_overdue": False, "is_escalated": False},
        {"approval_id": "a-3", "is_overdue": True, "is_escalated": False},
        {"approval_id": "a-4", "is_overdue": True, "is_escalated": True},
        {"approval_id": "a-5", "is_overdue": True, "is_escalated": False},
    ]
    anomalies = {
        "total_anomalies": 2,
        "no_candidates": [],
        "escalated_unresolved": [{"approval_id": "a-4"}],
        "overdue_not_escalated": [{"approval_id": "a-3"}],
    }
    export_json = [
        {"approval_id": "a-1"},
        {"approval_id": "a-2"},
        {"approval_id": "a-3"},
        {"approval_id": "a-4"},
        {"approval_id": "a-5"},
    ]
    (out_path / "summary.json").write_text(json.dumps(summary) + "\\n", encoding="utf-8")
    (out_path / "items.json").write_text(json.dumps(items) + "\\n", encoding="utf-8")
    (out_path / "anomalies.json").write_text(json.dumps(anomalies) + "\\n", encoding="utf-8")
    (out_path / "export.json").write_text(json.dumps(export_json) + "\\n", encoding="utf-8")
    (out_path / "export.csv").write_text("approval_id\\na-1\\na-2\\na-3\\na-4\\na-5\\n", encoding="utf-8")
    (out_path / "OBSERVATION_RESULT.md").write_text("# result\\n", encoding="utf-8")
    (out_path / "OBSERVATION_EVAL.md").write_text("# eval\\n- verdict: PASS\\n", encoding="utf-8")
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    (baseline_dir / "summary.json").write_text(
        json.dumps({"pending_count": 2, "overdue_count": 3, "escalated_count": 1}) + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "items.json").write_text(
        json.dumps(
            [
                {"approval_id": "a-1", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-2", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-3", "is_overdue": True, "is_escalated": False},
                {"approval_id": "a-4", "is_overdue": True, "is_escalated": True},
                {"approval_id": "a-5", "is_overdue": True, "is_escalated": False},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "anomalies.json").write_text(
        json.dumps(
            {
                "total_anomalies": 2,
                "no_candidates": [],
                "escalated_unresolved": [{"approval_id": "a-4"}],
                "overdue_not_escalated": [{"approval_id": "a-3"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "export.json").write_text(
        json.dumps(
            [
                {"approval_id": "a-1"},
                {"approval_id": "a-2"},
                {"approval_id": "a-3"},
                {"approval_id": "a-4"},
                {"approval_id": "a-5"},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "export.csv").write_text(
        "approval_id\na-1\na-2\na-3\na-4\na-5\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out-workflow-readonly"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    env["FAKE_GH_DISPATCH_LOG"] = str(dispatch_log)

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--output-dir",
            str(out_dir),
            "--baseline-dir",
            str(baseline_dir),
            "--no-restore",
            "--no-archive",
            "--eco-type",
            "ECR",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )

    assert cp.returncode == 0, cp.stdout + "\n" + cp.stderr
    assert "WORKFLOW_READONLY_DIFF.md" in cp.stdout
    assert "WORKFLOW_READONLY_EVAL.md" in cp.stdout
    assert (out_dir / "workflow-probe" / "WORKFLOW_DISPATCH_RESULT.md").is_file()
    assert (out_dir / "workflow-probe" / "artifact" / "summary.json").is_file()
    assert (out_dir / "WORKFLOW_READONLY_DIFF.md").is_file()
    assert (out_dir / "WORKFLOW_READONLY_EVAL.md").is_file()
    assert (out_dir / "WORKFLOW_READONLY_CHECK.md").is_file()

    eval_text = (out_dir / "WORKFLOW_READONLY_EVAL.md").read_text(encoding="utf-8")
    assert "- verdict: PASS" in eval_text

    summary_text = (out_dir / "WORKFLOW_READONLY_CHECK.md").read_text(encoding="utf-8")
    assert "workflow-probe/WORKFLOW_DISPATCH_RESULT.md" in summary_text
    assert "verdict: PASS" in summary_text

    dispatch_args = json.loads(dispatch_log.read_text(encoding="utf-8"))
    assert "base_url=http://142.171.239.56:7910" in dispatch_args
    assert "eco_type=ECR" in dispatch_args


def test_p2_shared_dev_142_workflow_readonly_check_wrapper_writes_failure_summary_on_probe_failure(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_shared_dev_142_workflow_readonly_check.sh"
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

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if args[:2] == ["repo", "view"]:
    print("zensgit/yuantus-plm")
    raise SystemExit(0)

if args[:2] == ["workflow", "run"]:
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    print(json.dumps([
        {
            "databaseId": 505,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2099-01-01T00:00:00Z",
        },
    ]))
    raise SystemExit(0)

if args[:3] == ["run", "watch", "505"]:
    raise SystemExit(1)

if args[:3] == ["run", "view", "505"] and "--json" in args and "--jq" in args:
    json_key = args[args.index("--json") + 1]
    jq_expr = args[args.index("--jq") + 1]
    if json_key == "status" and jq_expr == ".status":
        print("completed")
        raise SystemExit(0)
    if json_key == "conclusion" and jq_expr == ".conclusion":
        print("failure")
        raise SystemExit(0)
    if json_key == "url" and jq_expr == ".url":
        print("https://example.invalid/runs/505")
        raise SystemExit(0)

if args[:3] == ["run", "download", "505"]:
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
    if artifact_name != "p2-observation-regression":
        raise SystemExit(1)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "WORKFLOW_PRECHECK.md").write_text("# precheck\\n", encoding="utf-8")
    (out_path / "workflow_precheck.json").write_text(
        json.dumps(
            {
                "result": "failure",
                "reason": "missing authentication secret",
                "required": ["P2_OBSERVATION_TOKEN", "P2_OBSERVATION_PASSWORD"],
            }
        ) + "\\n",
        encoding="utf-8",
    )
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    out_dir = tmp_path / "out-workflow-readonly-failure"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--output-dir",
            str(out_dir),
            "--baseline-dir",
            str(baseline_dir),
            "--no-restore",
            "--no-archive",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )

    assert cp.returncode != 0
    assert (out_dir / "workflow-probe" / "WORKFLOW_DISPATCH_RESULT.md").is_file()
    assert (out_dir / "WORKFLOW_READONLY_CHECK.md").is_file()
    assert not (out_dir / "WORKFLOW_READONLY_DIFF.md").exists()
    assert not (out_dir / "WORKFLOW_READONLY_EVAL.md").exists()

    summary_text = (out_dir / "WORKFLOW_READONLY_CHECK.md").read_text(encoding="utf-8")
    assert "status: failure" in summary_text
    assert "missing authentication secret" in summary_text
    assert "P2_OBSERVATION_TOKEN" in summary_text
    assert "workflow-probe/WORKFLOW_DISPATCH_RESULT.md" in summary_text


def test_p2_shared_dev_142_workflow_readonly_check_wrapper_writes_failure_summary_on_eval_failure(tmp_path: Path) -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "run_p2_shared_dev_142_workflow_readonly_check.sh"
    assert script.is_file(), f"Missing script: {script}"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    dispatch_log = tmp_path / "dispatch_args.json"

    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]

if len(args) >= 2 and args[0] == "-R":
    args = args[2:]

if args[:2] == ["auth", "status"]:
    raise SystemExit(0)

if args[:2] == ["repo", "view"]:
    print("zensgit/yuantus-plm")
    raise SystemExit(0)

if args[:2] == ["workflow", "run"]:
    Path(os.environ["FAKE_GH_DISPATCH_LOG"]).write_text(
        json.dumps(args, ensure_ascii=True),
        encoding="utf-8",
    )
    raise SystemExit(0)

if args[:2] == ["run", "list"]:
    print(json.dumps([
        {
            "databaseId": 606,
            "event": "workflow_dispatch",
            "headBranch": "main",
            "createdAt": "2099-01-01T00:00:00Z",
        },
    ]))
    raise SystemExit(0)

if args[:3] == ["run", "watch", "606"]:
    raise SystemExit(0)

if args[:3] == ["run", "view", "606"] and "--json" in args and "--jq" in args:
    json_key = args[args.index("--json") + 1]
    jq_expr = args[args.index("--jq") + 1]
    if json_key == "status" and jq_expr == ".status":
        print("completed")
        raise SystemExit(0)
    if json_key == "conclusion" and jq_expr == ".conclusion":
        print("success")
        raise SystemExit(0)
    if json_key == "url" and jq_expr == ".url":
        print("https://example.invalid/runs/606")
        raise SystemExit(0)

if args[:3] == ["run", "download", "606"]:
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
    if artifact_name != "p2-observation-regression":
        raise SystemExit(1)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    summary = {
        "pending_count": 2,
        "overdue_count": 3,
        "escalated_count": 1,
    }
    items = [
        {"approval_id": "a-1", "is_overdue": False, "is_escalated": False},
        {"approval_id": "a-2", "is_overdue": False, "is_escalated": False},
        {"approval_id": "a-3", "is_overdue": True, "is_escalated": False},
        {"approval_id": "a-4", "is_overdue": True, "is_escalated": True},
        {"approval_id": "a-5", "is_overdue": True, "is_escalated": False},
    ]
    anomalies = {
        "total_anomalies": 2,
        "no_candidates": [],
        "escalated_unresolved": [{"approval_id": "a-4"}],
        "overdue_not_escalated": [{"approval_id": "a-3"}],
    }
    export_json = [
        {"approval_id": "a-1"},
        {"approval_id": "a-2"},
        {"approval_id": "a-3"},
        {"approval_id": "a-4"},
        {"approval_id": "a-5"},
    ]
    (out_path / "summary.json").write_text(json.dumps(summary) + "\\n", encoding="utf-8")
    (out_path / "items.json").write_text(json.dumps(items) + "\\n", encoding="utf-8")
    (out_path / "anomalies.json").write_text(json.dumps(anomalies) + "\\n", encoding="utf-8")
    (out_path / "export.json").write_text(json.dumps(export_json) + "\\n", encoding="utf-8")
    (out_path / "export.csv").write_text("approval_id\\na-1\\na-2\\na-3\\na-4\\na-5\\n", encoding="utf-8")
    (out_path / "OBSERVATION_RESULT.md").write_text("# result\\n", encoding="utf-8")
    (out_path / "OBSERVATION_EVAL.md").write_text("# eval\\n- verdict: PASS\\n", encoding="utf-8")
    raise SystemExit(0)

print("unexpected fake gh invocation: " + " ".join(args), file=sys.stderr)
raise SystemExit(2)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    fake_python = fake_bin / "python3"
    _write_fake_python_proxy(fake_python, evaluate_exit=19)

    baseline_dir = tmp_path / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    (baseline_dir / "summary.json").write_text(
        json.dumps({"pending_count": 2, "overdue_count": 3, "escalated_count": 1}) + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "items.json").write_text(
        json.dumps(
            [
                {"approval_id": "a-1", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-2", "is_overdue": False, "is_escalated": False},
                {"approval_id": "a-3", "is_overdue": True, "is_escalated": False},
                {"approval_id": "a-4", "is_overdue": True, "is_escalated": True},
                {"approval_id": "a-5", "is_overdue": True, "is_escalated": False},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "anomalies.json").write_text(
        json.dumps(
            {
                "total_anomalies": 2,
                "no_candidates": [],
                "escalated_unresolved": [{"approval_id": "a-4"}],
                "overdue_not_escalated": [{"approval_id": "a-3"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "export.json").write_text(
        json.dumps(
            [
                {"approval_id": "a-1"},
                {"approval_id": "a-2"},
                {"approval_id": "a-3"},
                {"approval_id": "a-4"},
                {"approval_id": "a-5"},
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (baseline_dir / "export.csv").write_text(
        "approval_id\na-1\na-2\na-3\na-4\na-5\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out-workflow-readonly-eval-failure"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
    env["FAKE_GH_DISPATCH_LOG"] = str(dispatch_log)

    cp = subprocess.run(  # noqa: S603
        [
            "bash",
            str(script),
            "--output-dir",
            str(out_dir),
            "--baseline-dir",
            str(baseline_dir),
            "--no-restore",
            "--no-archive",
            "--eco-type",
            "ECR",
        ],
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo_root),
    )

    assert cp.returncode != 0
    assert (out_dir / "workflow-probe" / "WORKFLOW_DISPATCH_RESULT.md").is_file()
    assert (out_dir / "workflow-probe" / "artifact" / "summary.json").is_file()
    assert (out_dir / "WORKFLOW_READONLY_DIFF.md").is_file()
    assert not (out_dir / "WORKFLOW_READONLY_EVAL.md").exists()
    assert not (out_dir / "WORKFLOW_READONLY_DIFF.log").exists()
    assert (out_dir / "WORKFLOW_READONLY_EVAL.log").is_file()
    assert (out_dir / "WORKFLOW_READONLY_CHECK.md").is_file()

    summary_text = (out_dir / "WORKFLOW_READONLY_CHECK.md").read_text(encoding="utf-8")
    assert "status: failure" in summary_text
    assert "readonly evaluation failed" in summary_text
    assert "WORKFLOW_READONLY_DIFF.md" in summary_text
    assert "WORKFLOW_READONLY_EVAL.log" in summary_text
    assert "verdict: unavailable" in summary_text

    eval_log_text = (out_dir / "WORKFLOW_READONLY_EVAL.log").read_text(encoding="utf-8")
    assert "synthetic evaluate failure" in eval_log_text

    dispatch_args = json.loads(dispatch_log.read_text(encoding="utf-8"))
    assert "base_url=http://142.171.239.56:7910" in dispatch_args
    assert "eco_type=ECR" in dispatch_args
