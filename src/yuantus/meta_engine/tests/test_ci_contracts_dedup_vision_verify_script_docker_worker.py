from __future__ import annotations

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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def test_verify_cad_dedup_vision_script_supports_docker_worker_mode() -> None:
    repo_root = _find_repo_root(Path(__file__))
    script = repo_root / "scripts" / "verify_cad_dedup_vision_s3.sh"
    assert script.is_file(), f"Missing script: {script}"

    text = _read(script)

    assert "USE_DOCKER_WORKER=" in text, (
        "verify_cad_dedup_vision_s3.sh should expose USE_DOCKER_WORKER env flag."
    )
    assert "pump_local_worker_once()" in text, (
        "verify_cad_dedup_vision_s3.sh should keep worker pumping behind a helper "
        "so docker-worker mode can disable local worker execution."
    )
    assert "wait_for_job_completed()" in text, (
        "verify_cad_dedup_vision_s3.sh should wait job completion via a reusable helper."
    )
    assert "result.ok is not true" in text, (
        "verify_cad_dedup_vision_s3.sh should fail when job payload.result.ok is not true."
    )

