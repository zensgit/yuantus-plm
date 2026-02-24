from __future__ import annotations

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
    payload = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace"))
    assert isinstance(payload, dict), f"workflow did not parse as mapping: {path}"
    return payload


def _needs_list(rel: str, job_id: str, raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        candidate = raw.strip()
        assert candidate, f"{rel} job '{job_id}' has empty needs string"
        return [candidate]
    assert isinstance(raw, list), f"{rel} job '{job_id}' needs must be string or list"

    values: list[str] = []
    for index, item in enumerate(raw):
        assert isinstance(item, str), f"{rel} job '{job_id}' needs[{index}] must be string"
        candidate = item.strip()
        assert candidate, f"{rel} job '{job_id}' needs[{index}] must be non-empty string"
        values.append(candidate)
    return values


def _assert_acyclic(rel: str, edges: dict[str, list[str]]) -> None:
    state: dict[str, int] = {node: 0 for node in edges}  # 0=unvisited,1=visiting,2=done

    def visit(node: str, path: list[str]) -> None:
        node_state = state[node]
        if node_state == 1:
            cycle = " -> ".join(path + [node])
            raise AssertionError(f"{rel} has cyclic job needs graph: {cycle}")
        if node_state == 2:
            return

        state[node] = 1
        for dep in edges[node]:
            visit(dep, path + [node])
        state[node] = 2

    for job_id in edges:
        visit(job_id, [])


def test_workflow_needs_graph_integrity() -> None:
    repo_root = _find_repo_root(Path(__file__))
    workflows = sorted((repo_root / ".github" / "workflows").glob("*.yml"))
    assert workflows, "No workflow files found under .github/workflows"

    for workflow in workflows:
        rel = workflow.relative_to(repo_root).as_posix()
        payload = _load_yaml(workflow)
        jobs = payload.get("jobs")
        assert isinstance(jobs, dict), f"{rel} must declare jobs mapping"
        assert jobs, f"{rel} must declare at least one job"

        job_ids = set(jobs.keys())
        edges: dict[str, list[str]] = {}
        for job_id, job_payload in jobs.items():
            assert isinstance(job_payload, dict), f"{rel} job '{job_id}' must be a mapping"
            deps = _needs_list(rel, str(job_id), job_payload.get("needs"))
            assert len(deps) == len(set(deps)), f"{rel} job '{job_id}' contains duplicate needs"

            for dep in deps:
                assert dep in job_ids, (
                    f"{rel} job '{job_id}' needs missing job '{dep}'; "
                    "all needs references must resolve to existing jobs"
                )
                assert dep != job_id, f"{rel} job '{job_id}' cannot depend on itself"

            edges[str(job_id)] = deps

        _assert_acyclic(rel, edges)
