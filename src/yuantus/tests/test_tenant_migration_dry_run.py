from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, text

from yuantus.scripts import tenant_migration_dry_run as dry_run
from yuantus.scripts.tenant_schema import GLOBAL_TABLE_NAMES, build_tenant_metadata


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def _create_full_tenant_source(path: Path) -> str:
    url = _sqlite_url(path)
    engine = create_engine(url)
    metadata = dry_run._build_import_metadata()
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("create table auth_users (id integer primary key)"))
        connection.execute(text("create table alembic_version (version_num text)"))
    engine.dispose()
    return url


def _create_partial_source(path: Path) -> str:
    url = _sqlite_url(path)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("create table meta_items (id integer primary key)"))
        connection.execute(text("insert into meta_items (id) values (1), (2)"))
        connection.execute(text("create table users (id integer primary key)"))
        connection.execute(text("create table alembic_version (version_num text)"))
        connection.execute(text("create table stray_table (id integer primary key)"))
    engine.dispose()
    return url


def test_import_order_excludes_global_tables_and_matches_stripped_metadata(tmp_path):
    report = dry_run.build_dry_run_report(
        _create_full_tenant_source(tmp_path / "source.db"),
        "Acme Prod",
    )
    expected_order = [table.name for table in dry_run._build_import_metadata().sorted_tables]

    assert report["tenant_tables_in_import_order"] == expected_order
    assert set(report["tenant_tables_in_import_order"]).isdisjoint(GLOBAL_TABLE_NAMES)
    assert set(report["global_tables"]) == set(GLOBAL_TABLE_NAMES)
    assert set(report["tenant_tables_in_import_order"]) == set(build_tenant_metadata().tables)


def test_full_source_with_global_tables_is_ready_and_excludes_globals(tmp_path):
    report = dry_run.build_dry_run_report(
        _create_full_tenant_source(tmp_path / "source.db"),
        "Acme Prod",
    )

    assert report["ready_for_import"] is True
    assert report["blockers"] == []
    assert report["missing_tenant_tables"] == []
    assert report["unknown_source_tables"] == []
    assert report["excluded_global_tables_present"] == ["auth_users"]
    assert "auth_users" not in report["row_counts"]
    assert set(report["row_counts"]) == set(report["tenant_tables_in_import_order"])


def test_partial_source_reports_counts_missing_unknown_and_allowed_metadata(tmp_path):
    report = dry_run.build_dry_run_report(
        _create_partial_source(tmp_path / "source.db"),
        "Acme Prod",
    )

    assert report["ready_for_import"] is False
    assert report["row_counts"]["meta_items"] == 2
    assert "users" in report["excluded_global_tables_present"]
    assert "stray_table" in report["unknown_source_tables"]
    assert "alembic_version" not in report["unknown_source_tables"]
    assert "meta_files" in report["missing_tenant_tables"]
    assert any("Unknown source tables: stray_table" == blocker for blocker in report["blockers"])


def test_source_url_password_is_redacted():
    redacted = dry_run._redact_source_url("postgresql://user:secret@example.com/db")

    assert "secret" not in redacted
    assert "user:***@" in redacted


def test_cli_writes_json_and_markdown_outputs(tmp_path):
    source_url = _create_partial_source(tmp_path / "source.db")
    json_path = tmp_path / "reports" / "dry-run.json"
    md_path = tmp_path / "reports" / "dry-run.md"

    result = dry_run.main(
        [
            "--source-url",
            source_url,
            "--tenant-id",
            "Acme Prod",
            "--output-json",
            str(json_path),
            "--output-md",
            str(md_path),
        ]
    )

    assert result == 0
    payload = json.loads(json_path.read_text())
    assert payload["schema_version"] == dry_run.SCHEMA_VERSION
    assert payload["target_schema"] == "yt_t_acme_prod"
    assert payload["ready_for_import"] is False
    markdown = md_path.read_text()
    assert "# Tenant Migration Dry-Run Report" in markdown
    assert "Unknown source tables: stray_table" in markdown


def test_cli_strict_exits_nonzero_when_blockers_exist(tmp_path):
    source_url = _create_partial_source(tmp_path / "source.db")

    result = dry_run.main(
        [
            "--source-url",
            source_url,
            "--tenant-id",
            "Acme Prod",
            "--output-json",
            str(tmp_path / "dry-run.json"),
            "--output-md",
            str(tmp_path / "dry-run.md"),
            "--strict",
        ]
    )

    assert result == 1


def test_cli_invalid_source_url_exits_two(tmp_path):
    result = dry_run.main(
        [
            "--source-url",
            "not a url",
            "--tenant-id",
            "Acme Prod",
            "--output-json",
            str(tmp_path / "dry-run.json"),
            "--output-md",
            str(tmp_path / "dry-run.md"),
        ]
    )

    assert result == 2


def test_dry_run_source_has_no_target_or_schema_creation_commands():
    source = Path(dry_run.__file__).read_text()
    upper_source = source.upper()

    assert "PROVISION_TENANT_SCHEMA" not in source
    assert "CREATE SCHEMA" not in upper_source
    assert "DROP SCHEMA" not in upper_source
    assert "TENANCY_MODE" not in source
