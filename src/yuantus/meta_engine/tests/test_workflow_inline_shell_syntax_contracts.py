from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import yaml


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / ".github").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + .github/)")


def _load_yaml(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    payload = yaml.safe_load(raw)
    assert isinstance(payload, dict), f"workflow did not parse as mapping: {path}"
    return payload


def _normalize_github_exprs(script: str) -> str:
    # GitHub expressions are expanded before shell execution; replace locally for syntax checking.
    return re.sub(r"\$\{\{.*?\}\}", "EXPR", script, flags=re.DOTALL)


def _bash_n(script: str, label: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=True) as fp:
        fp.write(script)
        fp.flush()
        cp = subprocess.run(  # noqa: S603,S607
            ["bash", "-n", fp.name],
            text=True,
            capture_output=True,
        )
    assert cp.returncode == 0, f"{label}\n{cp.stdout}\n{cp.stderr}"


def test_strict_gate_workflow_inline_run_scripts_are_bash_syntax_valid() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = (
        repo_root / ".github" / "workflows" / "strict-gate.yml",
        repo_root / ".github" / "workflows" / "strict-gate-recent-perf-regression.yml",
    )

    for wf in workflows:
        assert wf.is_file(), f"Missing workflow: {wf}"
        payload = _load_yaml(wf)
        jobs = payload.get("jobs")
        assert isinstance(jobs, dict), f"workflow jobs must be mapping: {wf}"

        run_steps_checked = 0
        for job_name, job in jobs.items():
            steps = job.get("steps") if isinstance(job, dict) else None
            if not isinstance(steps, list):
                continue
            for idx, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                run_script = step.get("run")
                if not isinstance(run_script, str):
                    continue
                normalized = _normalize_github_exprs(run_script)
                label = f"{wf}:{job_name}:step#{idx + 1}:{step.get('name', '(unnamed)')}"
                _bash_n(normalized, label)
                run_steps_checked += 1

        assert run_steps_checked > 0, f"No inline run steps checked for {wf}"
