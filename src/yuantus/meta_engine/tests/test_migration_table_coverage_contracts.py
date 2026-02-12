from __future__ import annotations

import re
from pathlib import Path

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.models.base import Base, WorkflowBase


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "pyproject.toml").is_file() and (cur / "migrations").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise AssertionError("Could not locate repo root (expected pyproject.toml + migrations/)")


def _migration_create_tables(repo_root: Path) -> set[str]:
    versions_dir = repo_root / "migrations" / "versions"
    assert versions_dir.is_dir(), f"Missing migrations versions dir: {versions_dir}"

    pattern = re.compile(r"""op\.create_table\(\s*["']([^"']+)["']""")
    names: set[str] = set()
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        names.update(pattern.findall(text))
    return names


def _model_tables() -> set[str]:
    import_all_models()

    # Keep these imports for side effects so auth/rbac tables are present in metadata.
    from yuantus.models import user as _user  # noqa: F401
    from yuantus.security.auth import models as _auth_models  # noqa: F401
    from yuantus.security.rbac import models as _rbac_models  # noqa: F401

    return set(Base.metadata.tables.keys()) | set(WorkflowBase.metadata.tables.keys())


def test_every_model_table_has_a_create_table_migration() -> None:
    repo_root = _find_repo_root(Path(__file__))
    migrated_tables = _migration_create_tables(repo_root)
    declared_tables = _model_tables()

    missing = sorted(declared_tables - migrated_tables)
    assert not missing, (
        "Some ORM-declared tables have no op.create_table migration contract. "
        "Add migration coverage for:\n"
        + "\n".join(f"- {name}" for name in missing)
    )


def test_migration_only_tables_are_allowlisted() -> None:
    repo_root = _find_repo_root(Path(__file__))
    migrated_tables = _migration_create_tables(repo_root)
    declared_tables = _model_tables()

    extra = sorted(migrated_tables - declared_tables)
    allowed = {"audit_logs"}
    unexpected = sorted(name for name in extra if name not in allowed)
    assert not unexpected, (
        "Migrations define tables no longer declared in ORM metadata. "
        "If intentional, document and allowlist explicitly:\n"
        + "\n".join(f"- {name}" for name in unexpected)
    )

