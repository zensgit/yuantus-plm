from __future__ import annotations

from contextlib import contextmanager
from threading import RLock
from typing import Generator, Optional

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from yuantus.config import get_settings
from yuantus.database import create_db_engine


_lock = RLock()
_engine: Optional[Engine] = None
_sessionmaker: Optional[sessionmaker] = None
_engine_url: Optional[str] = None


def get_identity_database_url() -> str:
    settings = get_settings()
    return settings.IDENTITY_DATABASE_URL or settings.DATABASE_URL


def get_identity_engine() -> Engine:
    global _engine, _sessionmaker, _engine_url
    url = get_identity_database_url()
    with _lock:
        if _engine is not None and _engine_url == url:
            return _engine

        _engine = create_db_engine(url)
        _sessionmaker = sessionmaker(
            autocommit=False, autoflush=False, expire_on_commit=False, bind=_engine
        )
        _engine_url = url
        return _engine


def get_identity_sessionmaker() -> sessionmaker:
    get_identity_engine()
    assert _sessionmaker is not None
    return _sessionmaker


def init_identity_db(*, create_tables: bool = False) -> None:
    if not create_tables:
        return
    settings = get_settings()
    engine = get_identity_engine()
    from yuantus.models.base import Base, WorkflowBase
    from yuantus.security.auth import models as _auth_models  # noqa: F401

    # In SCHEMA_MODE=migrations, never auto-create tables (avoid masking Alembic issues).
    if settings.SCHEMA_MODE == "migrations":
        from sqlalchemy import inspect

        existing_tables = set(inspect(engine).get_table_names())
        required_tables = {
            "auth_tenants",
            "auth_organizations",
            "auth_users",
            "auth_credentials",
            "auth_org_memberships",
            "auth_tenant_quotas",
        }
        missing = sorted(required_tables - existing_tables)
        if missing:
            raise RuntimeError(
                "SCHEMA_MODE=migrations: Identity schema is missing tables: "
                + ", ".join(missing)
                + ". Run `yuantus db upgrade` first to create tables via Alembic."
            )
        return

    # NOTE: In early-stage/dev we use create_all; production should use migrations.
    Base.metadata.create_all(bind=engine, checkfirst=True)
    WorkflowBase.metadata.create_all(bind=engine, checkfirst=True)


def get_identity_db() -> Generator[Session, None, None]:
    SessionLocal = get_identity_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_identity_db_session() -> Generator[Session, None, None]:
    SessionLocal = get_identity_sessionmaker()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
