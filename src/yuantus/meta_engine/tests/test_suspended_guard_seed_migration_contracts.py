from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "migrations").is_dir():
            return cur
        cur = cur.parent
    raise AssertionError("repo root not found")


def test_lifecycle_state_is_suspended_migration_contract() -> None:
    repo = _repo_root()
    path = repo / "migrations" / "versions" / "f4a5b6c7d8e9_add_lifecycle_state_is_suspended.py"
    text = path.read_text(encoding="utf-8")

    assert "down_revision: Union[str, None] = \"e3f4a5b6c7d8\"" in text
    assert "\"meta_lifecycle_states\"" in text
    assert "\"is_suspended\"" in text
    assert "server_default=sa.false()" in text
    assert "batch_alter_table" in text
    assert "drop_column(_COLUMN)" in text


def test_registry_lifecycle_seeder_marks_part_suspended_state() -> None:
    repo = _repo_root()
    text = (repo / "src" / "yuantus" / "seeder" / "meta" / "lifecycles.py").read_text(
        encoding="utf-8"
    )

    assert "is_suspended=False" in text
    assert '"Suspended", lock=True, seq=35, is_suspended=True' in text


def test_cli_seed_meta_marks_part_suspended_state() -> None:
    repo = _repo_root()
    text = (repo / "src" / "yuantus" / "cli.py").read_text(encoding="utf-8")

    assert "is_suspended: bool = False" in text
    assert "state.is_suspended = is_suspended" in text
    assert "part_suspended_state = ensure_state" in text
    assert "is_suspended=True" in text
