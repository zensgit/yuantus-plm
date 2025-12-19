"""
Database configuration and session management.

This module is intentionally small and test-friendly:
- Defaults to SQLite for local dev
- Supports Postgres via DATABASE_URL
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from threading import RLock
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from yuantus.config import get_settings
from yuantus.context import org_id_var, tenant_id_var
from yuantus.models.base import Base, WorkflowBase


def get_database_url() -> str:
    settings = get_settings()
    return settings.DATABASE_URL


def _sanitize_tenant_id(raw: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    cleaned = "".join(ch if ch in allowed else "_" for ch in raw.strip())
    return cleaned or "default"


def resolve_database_url(*, tenant_id: Optional[str] = None, org_id: Optional[str] = None) -> str:
    """
    Resolve database URL for the current tenancy mode.

    - TENANCY_MODE=single: always returns DATABASE_URL
    - TENANCY_MODE=db-per-tenant: returns DATABASE_URL_TEMPLATE (if set) or a derived URL for sqlite
    """
    settings = get_settings()
    if settings.TENANCY_MODE not in {"db-per-tenant", "db-per-tenant-org"}:
        return settings.DATABASE_URL

    effective_tenant = _sanitize_tenant_id(tenant_id or "default")
    effective_org = _sanitize_tenant_id(org_id or "default")

    if settings.DATABASE_URL_TEMPLATE:
        return settings.DATABASE_URL_TEMPLATE.format(
            tenant_id=effective_tenant, org_id=effective_org
        )

    # Dev-friendly default: if sqlite file, derive per-tenant filename.
    url = settings.DATABASE_URL
    if url.startswith("sqlite:///") and url.endswith(".db"):
        base = url[len("sqlite:///") : -len(".db")]
        if settings.TENANCY_MODE == "db-per-tenant-org":
            return f"sqlite:///{base}__{effective_tenant}__{effective_org}.db"
        return f"sqlite:///{base}__{effective_tenant}.db"

    # Fallback: without explicit template we cannot safely derive for other DBs.
    return url


def create_db_engine(database_url: Optional[str] = None, *, echo: bool = False):
    url = database_url or get_database_url()

    connect_args: dict = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False

    if url.startswith("sqlite:///:memory:"):
        from sqlalchemy.pool import StaticPool

        engine = create_engine(
            url,
            echo=echo,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(
            url,
            echo=echo,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args=connect_args,
        )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):  # pragma: no cover
        if "sqlite" in url:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


if os.getenv("ALEMBIC_RUNNING") != "true":
    engine = create_db_engine()
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
    )
else:  # pragma: no cover
    engine = None
    SessionLocal = None


_tenant_engines: dict[str, Engine] = {}
_tenant_sessions: dict[str, sessionmaker] = {}
_tenant_init_done: set[str] = set()
_tenant_lock = RLock()


def get_engine_for_scope(tenant_id: Optional[str], org_id: Optional[str]) -> Engine:
    url = resolve_database_url(tenant_id=tenant_id, org_id=org_id)
    with _tenant_lock:
        existing = _tenant_engines.get(url)
        if existing is not None:
            return existing

        eng = create_db_engine(url)
        _tenant_engines[url] = eng
        _tenant_sessions[url] = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=eng
        )
        return eng


def get_sessionmaker_for_scope(tenant_id: Optional[str], org_id: Optional[str]) -> sessionmaker:
    url = resolve_database_url(tenant_id=tenant_id, org_id=org_id)
    with _tenant_lock:
        if url not in _tenant_sessions:
            eng = get_engine_for_scope(tenant_id, org_id)
            _tenant_sessions[url] = sessionmaker(
                autocommit=False, autoflush=False, expire_on_commit=False, bind=eng
            )
        return _tenant_sessions[url]

def get_engine_for_tenant(tenant_id: Optional[str]) -> Engine:
    return get_engine_for_scope(tenant_id, None)


def get_sessionmaker_for_tenant(tenant_id: Optional[str]) -> sessionmaker:
    return get_sessionmaker_for_scope(tenant_id, None)


def get_db() -> Generator[Session, None, None]:
    settings = get_settings()
    if settings.TENANCY_MODE in {"db-per-tenant", "db-per-tenant-org"}:
        tenant_id = tenant_id_var.get()
        org_id = org_id_var.get() if settings.TENANCY_MODE == "db-per-tenant-org" else None
        url = resolve_database_url(tenant_id=tenant_id, org_id=org_id)
        with _tenant_lock:
            sess_factory = _tenant_sessions.get(url)
            if sess_factory is None:
                eng = get_engine_for_scope(tenant_id, org_id)
                sess_factory = _tenant_sessions[url]

            # Dev convenience: initialize schema once per tenant DB (only in create_all mode).
            if (
                settings.ENVIRONMENT == "dev"
                and settings.SCHEMA_MODE == "create_all"
                and url not in _tenant_init_done
            ):
                init_db(create_tables=True, bind_engine=_tenant_engines[url])
                _tenant_init_done.add(url)

        db = sess_factory()
    else:
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    settings = get_settings()
    if settings.TENANCY_MODE in {"db-per-tenant", "db-per-tenant-org"}:
        tenant_id = tenant_id_var.get()
        org_id = org_id_var.get() if settings.TENANCY_MODE == "db-per-tenant-org" else None
        sess_factory = get_sessionmaker_for_scope(tenant_id, org_id)
        session = sess_factory()
    else:
        session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(*, create_tables: bool = False, bind_engine: Optional[Engine] = None) -> None:
    """
    Initialize database schema.

    When SCHEMA_MODE=migrations, this will NOT auto-create tables.
    Use `yuantus db upgrade` for production deployments.
    """
    settings = get_settings()
    target_engine = bind_engine or engine
    if not target_engine:
        raise RuntimeError("Database engine is not initialized")

    if create_tables:
        # Block auto-creation in migrations mode
        if settings.SCHEMA_MODE == "migrations":
            # Check if tables exist; if not, raise helpful error
            from sqlalchemy import inspect

            inspector = inspect(target_engine)
            existing_tables = inspector.get_table_names()
            if not existing_tables:
                raise RuntimeError(
                    "SCHEMA_MODE=migrations: Database is empty. "
                    "Run `yuantus db upgrade` first to create tables via Alembic."
                )
            return  # Tables exist, skip create_all

        # create_all mode: auto-create tables
        # Ensure all Meta Engine models are registered before create_all().
        from yuantus.meta_engine.bootstrap import import_all_models

        import_all_models()

        # Ensure core tables referenced by FK constraints are registered.
        from yuantus.models import user as _user  # noqa: F401

        Base.metadata.create_all(bind=target_engine, checkfirst=True)
        WorkflowBase.metadata.create_all(bind=target_engine, checkfirst=True)
