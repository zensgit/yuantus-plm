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
