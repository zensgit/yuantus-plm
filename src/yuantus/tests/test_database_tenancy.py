"""
P3.2 tenancy tests — schema name resolver unit tests + dispatch contracts.

Postgres-specific pool-safety test is guarded by YUANTUS_TEST_PG_DSN and skips
cleanly when that env var is absent.
"""
from __future__ import annotations

import os
import pytest

from yuantus.database import (
    MissingTenantContextError,
    _PG_MAX_IDENTIFIER,
    _SCHEMA_PREFIX,
    tenant_id_to_schema,
)


# ---------------------------------------------------------------------------
# Schema resolver — normalisation
# ---------------------------------------------------------------------------


def test_uppercase_is_lowercased():
    assert tenant_id_to_schema("Acme") == "yt_t_acme"


def test_lowercase_passthrough():
    assert tenant_id_to_schema("acme") == "yt_t_acme"


def test_dash_replaced_with_underscore():
    assert tenant_id_to_schema("acme-tenant") == "yt_t_acme_tenant"


def test_space_replaced_with_underscore():
    assert tenant_id_to_schema("acme corp") == "yt_t_acme_corp"


def test_punctuation_replaced():
    result = tenant_id_to_schema("acme corp!")
    assert result == "yt_t_acme_corp_"
    assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in result)


def test_digits_preserved():
    assert tenant_id_to_schema("tenant42") == "yt_t_tenant42"


def test_sql_injection_sanitised():
    result = tenant_id_to_schema('acme"; DROP SCHEMA x; --')
    assert '"' not in result
    assert ";" not in result
    assert " " not in result
    assert result.startswith(_SCHEMA_PREFIX)


def test_unicode_only_input_is_rejected():
    # All non-ASCII chars map to "_"; after sanitisation the name has no valid chars.
    with pytest.raises(ValueError):
        tenant_id_to_schema("客户")


# ---------------------------------------------------------------------------
# Schema resolver — rejection cases
# ---------------------------------------------------------------------------


def test_empty_string_raises():
    with pytest.raises(MissingTenantContextError):
        tenant_id_to_schema("")


def test_whitespace_only_raises():
    with pytest.raises(MissingTenantContextError):
        tenant_id_to_schema("   ")


def test_none_raises():
    with pytest.raises(MissingTenantContextError):
        tenant_id_to_schema(None)


def test_all_punctuation_raises():
    with pytest.raises(ValueError):
        tenant_id_to_schema("!!!")


def test_all_non_ascii_raises_or_maps_to_underscores_then_raises():
    # "客户" maps to "___" after sanitisation — all underscores → rejected
    with pytest.raises(ValueError):
        tenant_id_to_schema("客户客户客户")


# ---------------------------------------------------------------------------
# Schema resolver — truncation and stability
# ---------------------------------------------------------------------------


def test_short_input_within_max():
    result = tenant_id_to_schema("acme")
    assert len(result) <= _PG_MAX_IDENTIFIER


def test_long_input_truncated_to_max():
    long_id = "a" * 100
    result = tenant_id_to_schema(long_id)
    assert len(result) == _PG_MAX_IDENTIFIER


def test_truncation_is_stable():
    long_id = "a" * 100
    assert tenant_id_to_schema(long_id) == tenant_id_to_schema(long_id)


def test_truncation_hash_differs_for_different_inputs():
    long_a = "a" * 100
    long_b = "b" * 100
    result_a = tenant_id_to_schema(long_a)
    result_b = tenant_id_to_schema(long_b)
    assert result_a != result_b


def test_output_always_starts_with_prefix():
    for tid in ["acme", "Acme Corp", "tenant-1", "x" * 80]:
        result = tenant_id_to_schema(tid)
        assert result.startswith(_SCHEMA_PREFIX), f"{tid!r} → {result!r}"


# ---------------------------------------------------------------------------
# Dispatch contracts — schema-per-tenant mode raises without context
# ---------------------------------------------------------------------------


def test_get_db_raises_400_without_tenant_context(monkeypatch):
    """get_db() in schema-per-tenant mode must raise HTTPException(400) when
    tenant_id ContextVar is not set, before any DB access."""
    from fastapi import HTTPException
    from yuantus.config import get_settings
    from yuantus.context import tenant_id_var

    settings = get_settings()
    original = settings.TENANCY_MODE
    settings.TENANCY_MODE = "schema-per-tenant"
    token = tenant_id_var.set(None)
    try:
        gen = __import__("yuantus.database", fromlist=["get_db"]).get_db()
        with pytest.raises(HTTPException) as exc_info:
            next(gen)
        assert exc_info.value.status_code == 400
    finally:
        settings.TENANCY_MODE = original
        tenant_id_var.reset(token)


def test_get_db_session_raises_runtime_error_without_tenant_context(monkeypatch):
    """get_db_session() in schema-per-tenant mode must raise RuntimeError when
    tenant_id ContextVar is not set."""
    from yuantus.config import get_settings
    from yuantus.context import tenant_id_var
    from yuantus.database import get_db_session

    settings = get_settings()
    original = settings.TENANCY_MODE
    settings.TENANCY_MODE = "schema-per-tenant"
    token = tenant_id_var.set(None)
    try:
        with pytest.raises(RuntimeError):
            with get_db_session():
                pass
    finally:
        settings.TENANCY_MODE = original
        tenant_id_var.reset(token)


# ---------------------------------------------------------------------------
# Postgres-only guard — non-Postgres URLs rejected before session creation
# ---------------------------------------------------------------------------


def test_get_db_raises_400_for_non_postgres_url():
    """schema-per-tenant with a SQLite DATABASE_URL must raise HTTPException(400)
    before any session is opened, with a message that names 'postgres'."""
    from fastapi import HTTPException
    from yuantus.config import get_settings
    from yuantus.context import tenant_id_var
    import yuantus.database as db_module

    settings = get_settings()
    original_mode = settings.TENANCY_MODE
    settings.TENANCY_MODE = "schema-per-tenant"
    token = tenant_id_var.set("tenant1")  # valid — avoids missing-context error
    try:
        gen = db_module.get_db()
        with pytest.raises(HTTPException) as exc_info:
            next(gen)
        assert exc_info.value.status_code == 400
        assert "postgres" in exc_info.value.detail.lower()
    finally:
        settings.TENANCY_MODE = original_mode
        tenant_id_var.reset(token)


def test_get_db_session_raises_runtime_error_for_non_postgres_url():
    """get_db_session() in schema-per-tenant mode with a SQLite URL must raise
    RuntimeError with a Postgres-specific message before any session is opened."""
    from yuantus.config import get_settings
    from yuantus.context import tenant_id_var
    from yuantus.database import get_db_session

    settings = get_settings()
    original_mode = settings.TENANCY_MODE
    settings.TENANCY_MODE = "schema-per-tenant"
    token = tenant_id_var.set("tenant1")
    try:
        with pytest.raises(RuntimeError, match="(?i)postgres"):
            with get_db_session():
                pass
    finally:
        settings.TENANCY_MODE = original_mode
        tenant_id_var.reset(token)


# ---------------------------------------------------------------------------
# Existing-mode regression — single mode is unaffected
# ---------------------------------------------------------------------------


def test_single_mode_get_db_does_not_invoke_schema_resolver(monkeypatch):
    """In single mode, tenant_id_to_schema must never be called."""
    from yuantus.config import get_settings
    from yuantus import database as db_module

    settings = get_settings()
    original = settings.TENANCY_MODE
    settings.TENANCY_MODE = "single"
    called = []

    real_resolver = db_module.tenant_id_to_schema
    monkeypatch.setattr(db_module, "tenant_id_to_schema", lambda *a, **kw: called.append(1) or real_resolver(*a, **kw))
    try:
        gen = db_module.get_db()
        db = next(gen)
        try:
            gen.close()
        except StopIteration:
            pass
    finally:
        settings.TENANCY_MODE = original

    assert not called, "tenant_id_to_schema must not be called in single mode"


# ---------------------------------------------------------------------------
# Postgres pool-safety — skips when no test DSN provided
# ---------------------------------------------------------------------------

_PG_DSN = os.environ.get("YUANTUS_TEST_PG_DSN")


@pytest.mark.skipif(not _PG_DSN, reason="YUANTUS_TEST_PG_DSN not set — Postgres pool-safety test skipped")
def test_schema_search_path_does_not_leak_between_transactions():
    """Two consecutive schema-per-tenant sessions on the same Postgres connection
    must not see each other's search_path after commit (SET LOCAL guarantee)."""
    from sqlalchemy import create_engine, text as sa_text
    from sqlalchemy.orm import sessionmaker as make_sessionmaker

    engine = create_engine(_PG_DSN, pool_size=1, max_overflow=0)
    Session = make_sessionmaker(bind=engine)

    schema_a = tenant_id_to_schema("pool_safety_tenant_a")
    schema_b = tenant_id_to_schema("pool_safety_tenant_b")

    with engine.connect() as conn:
        conn.execute(sa_text(f'CREATE SCHEMA IF NOT EXISTS "{schema_a}"'))
        conn.execute(sa_text(f'CREATE SCHEMA IF NOT EXISTS "{schema_b}"'))
        conn.commit()

    try:
        s1 = Session()
        s1.execute(sa_text(f'SET LOCAL search_path TO "{schema_a}", public'))
        path_during_a = s1.execute(sa_text("SHOW search_path")).scalar()
        s1.commit()
        s1.close()

        s2 = Session()
        s2.execute(sa_text(f'SET LOCAL search_path TO "{schema_b}", public'))
        path_during_b = s2.execute(sa_text("SHOW search_path")).scalar()
        s2.commit()
        s2.close()

        assert schema_a in path_during_a, f"session A search_path: {path_during_a}"
        assert schema_b in path_during_b, f"session B search_path: {path_during_b}"
        assert schema_a not in path_during_b, (
            f"session B leaked schema_a in search_path: {path_during_b}"
        )
    finally:
        with engine.connect() as conn:
            conn.execute(sa_text(f'DROP SCHEMA IF EXISTS "{schema_a}"'))
            conn.execute(sa_text(f'DROP SCHEMA IF EXISTS "{schema_b}"'))
            conn.commit()
        engine.dispose()


@pytest.mark.skipif(not _PG_DSN, reason="YUANTUS_TEST_PG_DSN not set — after_begin re-apply test skipped")
def test_search_path_reapplied_after_intermediate_commit():
    """The after_begin event listener must re-apply SET LOCAL on every new
    transaction so that db.refresh() or queries after db.commit() still see
    the tenant schema — not just the first query in the session."""
    from sqlalchemy import create_engine, event as sa_event, text as sa_text
    from sqlalchemy.orm import sessionmaker as make_sessionmaker

    schema = tenant_id_to_schema("reapply_after_commit_tenant")
    engine = create_engine(_PG_DSN, pool_size=1, max_overflow=0)
    Session = make_sessionmaker(bind=engine)

    with engine.connect() as conn:
        conn.execute(sa_text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.commit()

    try:
        session = Session()

        @sa_event.listens_for(session, "after_begin")
        def _apply(sess, transaction, connection):
            connection.execute(sa_text(f'SET LOCAL search_path TO "{schema}", public'))

        # First transaction — after_begin fires, SET LOCAL applied
        path_before_commit = session.execute(sa_text("SHOW search_path")).scalar()
        session.commit()  # SET LOCAL expires here

        # Second transaction — after_begin must fire again, re-applying SET LOCAL
        path_after_commit = session.execute(sa_text("SHOW search_path")).scalar()
        session.close()

        assert schema in path_before_commit, f"before commit: {path_before_commit}"
        assert schema in path_after_commit, (
            f"after commit search_path reverted — after_begin did not re-apply: "
            f"{path_after_commit}"
        )
    finally:
        with engine.connect() as conn:
            conn.execute(sa_text(f'DROP SCHEMA IF EXISTS "{schema}"'))
            conn.commit()
        engine.dispose()
