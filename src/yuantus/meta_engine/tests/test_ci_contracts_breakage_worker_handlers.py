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


def test_cli_worker_registers_breakage_job_handlers() -> None:
    repo_root = _find_repo_root(Path(__file__))
    cli_py = repo_root / "src" / "yuantus" / "cli.py"
    assert cli_py.is_file()
    text = _read(cli_py)

    assert "from yuantus.meta_engine.tasks.breakage_tasks import" in text, (
        "Worker CLI should import breakage task handlers."
    )
    assert 'w.register_handler("breakage_helpdesk_sync_stub", breakage_helpdesk_sync_stub)' in text, (
        "Worker CLI should register breakage_helpdesk_sync_stub handler."
    )
    assert 'w.register_handler("breakage_incidents_export", breakage_incidents_export)' in text, (
        "Worker CLI should register breakage_incidents_export handler."
    )
    assert "breakage_incidents_export_cleanup" in text, (
        "Worker CLI should register breakage_incidents_export_cleanup handler."
    )


def test_breakage_tasks_module_exposes_worker_entrypoints() -> None:
    repo_root = _find_repo_root(Path(__file__))
    task_py = (
        repo_root
        / "src"
        / "yuantus"
        / "meta_engine"
        / "tasks"
        / "breakage_tasks.py"
    )
    assert task_py.is_file(), "Missing tasks module: src/yuantus/meta_engine/tasks/breakage_tasks.py"
    text = _read(task_py)

    assert "def breakage_helpdesk_sync_stub(" in text
    assert "def breakage_incidents_export(" in text
    assert "def breakage_incidents_export_cleanup(" in text
