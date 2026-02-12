from __future__ import annotations

from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "src").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + src/)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_cad_dedup_job_promotion_index_true_is_supported() -> None:
    repo_root = _find_repo_root(Path(__file__))
    job_service_py = (
        repo_root
        / "src"
        / "yuantus"
        / "meta_engine"
        / "services"
        / "job_service.py"
    )
    job_worker_py = (
        repo_root
        / "src"
        / "yuantus"
        / "meta_engine"
        / "services"
        / "job_worker.py"
    )

    service_text = _read(job_service_py)
    assert "task_type == \"cad_dedup_vision\"" in service_text, (
        "JobService.create_job should have a cad_dedup_vision special-case for promotion."
    )
    assert "want_index = bool(payload.get(\"index\", False))" in service_text, (
        "JobService.create_job must check payload index flag for promotion "
        '(expected exact snippet: want_index = bool(payload.get("index", False))).'
    )
    assert "cur[\"index\"] = True" in service_text, (
        "JobService.create_job must be able to promote an existing job payload to index=true "
        '(expected exact snippet: cur["index"] = True).'
    )

    worker_text = _read(job_worker_py)
    assert "job_service.session.refresh(job)" in worker_text, (
        "Worker must refresh job payload before execution so late promotions "
        "(e.g. index=true) are picked up."
    )
