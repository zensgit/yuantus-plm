from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

_SCRIPT_IN_RUN_RE = re.compile(
    r"(?:^|[;&|]\s*|\s)(?:bash|python|python3)\s+"
    r"(?:\./)?(scripts/[A-Za-z0-9_./-]+\.(?:sh|py))(?![A-Za-z0-9_.-])",
    flags=re.MULTILINE,
)
_SCRIPT_PATH_ONLY_RE = re.compile(r"^(?:\./)?(scripts/[A-Za-z0-9_./-]+\.(?:sh|py))$")


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
    payload = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    assert isinstance(payload, dict), f"workflow did not parse as mapping: {path}"
    return payload


def _workflow_on_block(payload: dict) -> Any:
    # PyYAML may parse top-level 'on' as boolean True with YAML 1.1 rules.
    return payload.get("on") if "on" in payload else payload.get(True)


def _normalize_path_entry(raw: str) -> str | None:
    path = raw.strip().strip("'\"")
    match = _SCRIPT_PATH_ONLY_RE.match(path)
    if not match:
        return None
    normalized = match.group(1)
    if any(ch in normalized for ch in "*?[]{}!"):
        return None
    return normalized


def _extract_script_refs_from_paths(node: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if str(key) == "paths" and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        normalized = _normalize_path_entry(item)
                        if normalized:
                            refs.add(normalized)
            refs.update(_extract_script_refs_from_paths(value))
    elif isinstance(node, list):
        for item in node:
            refs.update(_extract_script_refs_from_paths(item))
    return refs


def _extract_script_refs_from_job_runs(payload: dict) -> set[str]:
    refs: set[str] = set()
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict):
        return refs
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            run_script = step.get("run")
            if not isinstance(run_script, str):
                continue
            refs.update(match.group(1) for match in _SCRIPT_IN_RUN_RE.finditer(run_script))
    return refs


def _collect_workflow_script_refs(repo_root: Path) -> dict[Path, set[str]]:
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    refs_by_workflow: dict[Path, set[str]] = {}
    for workflow in workflows:
        payload = _load_yaml(workflow)
        refs = _extract_script_refs_from_job_runs(payload)
        refs.update(_extract_script_refs_from_paths(_workflow_on_block(payload)))
        refs_by_workflow[workflow] = refs
    return refs_by_workflow


def _bash_n(script: Path) -> None:
    cp = subprocess.run(  # noqa: S603,S607
        ["bash", "-n", str(script)],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, f"{script}\n{cp.stdout}\n{cp.stderr}"


def test_workflow_script_references_point_to_existing_files() -> None:
    repo_root = _find_repo_root(Path(__file__))
    refs_by_workflow = _collect_workflow_script_refs(repo_root)

    all_refs = sorted({ref for refs in refs_by_workflow.values() for ref in refs})
    assert all_refs, "No local scripts discovered from workflow references"

    missing: list[str] = []
    for workflow, refs in refs_by_workflow.items():
        rel_workflow = workflow.relative_to(repo_root).as_posix()
        for ref in sorted(refs):
            if not (repo_root / ref).is_file():
                missing.append(f"{rel_workflow} -> {ref}")
    assert not missing, "Workflow references missing scripts:\n" + "\n".join(missing)


def test_workflow_referenced_shell_scripts_are_bash_syntax_valid() -> None:
    repo_root = _find_repo_root(Path(__file__))
    refs_by_workflow = _collect_workflow_script_refs(repo_root)
    shell_refs = sorted({ref for refs in refs_by_workflow.values() for ref in refs if ref.endswith(".sh")})
    assert shell_refs, "No shell scripts discovered from workflow references"

    for ref in shell_refs:
        script = repo_root / ref
        assert script.is_file(), f"Missing script: {script}"
        _bash_n(script)
