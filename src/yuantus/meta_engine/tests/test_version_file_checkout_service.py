from __future__ import annotations

from sqlalchemy import Column, String, Table, create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from yuantus.models.base import Base
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.version.file_service import (
    VersionFileError,
    VersionFileService,
)
from yuantus.meta_engine.version.models import ItemVersion, VersionFile
from yuantus.security.rbac.models import RBACUser


@pytest.fixture
def db_session():
    meta_items = Table(
        "meta_items",
        Base.metadata,
        Column("id", String, primary_key=True),
        extend_existing=True,
    )
    meta_vaults = Table(
        "meta_vaults",
        Base.metadata,
        Column("id", String, primary_key=True),
        extend_existing=True,
    )
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            RBACUser.__table__,
            meta_items,
            meta_vaults,
            FileContainer.__table__,
            ItemVersion.__table__,
            VersionFile.__table__,
        ],
    )
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        session.add_all(
            [
                RBACUser(id=7, user_id=7, username="alice"),
                RBACUser(id=9, user_id=9, username="bob"),
            ]
        )
        session.execute(
            meta_items.insert().values(
                id="item-1",
                config_id="item-1",
            )
        )
        session.add(
            ItemVersion(
                id="ver-1",
                item_id="item-1",
                generation=1,
                revision="A",
                version_label="1.A",
                state="Draft",
                is_current=True,
            )
        )
        session.add_all(
            [
                FileContainer(
                    id="file-1",
                    filename="assembly.step",
                    file_type="step",
                    system_path="vault/file-1.step",
                ),
                FileContainer(
                    id="file-2",
                    filename="assembly.png",
                    file_type="png",
                    system_path="vault/file-2.png",
                ),
            ]
        )
        session.add_all(
            [
                VersionFile(
                    id="vf-1",
                    version_id="ver-1",
                    file_id="file-1",
                    file_role="native_cad",
                    sequence=0,
                    is_primary=True,
                ),
                VersionFile(
                    id="vf-2",
                    version_id="ver-1",
                    file_id="file-2",
                    file_role="preview",
                    sequence=1,
                ),
            ]
        )
        session.commit()
        yield session
    finally:
        session.close()


def test_checkout_file_happy_path_sets_lock(db_session):
    service = VersionFileService(db_session)

    assoc = service.checkout_file("ver-1", "file-2", user_id=7, file_role="preview")

    assert assoc.checked_out_by_id == 7
    assert assoc.checked_out_at is not None
    lock = service.get_file_lock("ver-1", "file-2", file_role="preview")
    assert lock["checked_out_by_id"] == 7
    assert lock["checked_out_at"] is not None


def test_checkout_file_requires_file_role_when_file_is_attached_multiple_times(db_session):
    db_session.add(
        VersionFile(
            id="vf-3",
            version_id="ver-1",
            file_id="file-2",
            file_role="geometry",
            sequence=2,
        )
    )
    db_session.commit()

    service = VersionFileService(db_session)

    with pytest.raises(VersionFileError, match="specify file_role"):
        service.checkout_file("ver-1", "file-2", user_id=7)


def test_checkout_file_rejects_released_or_foreign_version_lock(db_session):
    version = db_session.get(ItemVersion, "ver-1")
    version.is_released = True
    db_session.add(version)
    db_session.commit()

    service = VersionFileService(db_session)
    with pytest.raises(VersionFileError, match="released and locked"):
        service.checkout_file("ver-1", "file-2", user_id=7, file_role="preview")

    version.is_released = False
    version.checked_out_by_id = 9
    db_session.add(version)
    db_session.commit()

    with pytest.raises(VersionFileError, match="checked out by another user"):
        service.checkout_file("ver-1", "file-2", user_id=7, file_role="preview")


def test_release_all_file_locks_clears_version_bindings(db_session):
    service = VersionFileService(db_session)
    service.checkout_file("ver-1", "file-1", user_id=7, file_role="native_cad")
    service.checkout_file("ver-1", "file-2", user_id=7, file_role="preview")

    released = service.release_all_file_locks("ver-1")

    assert released == 2
    locks = service.get_blocking_file_locks("ver-1")
    assert locks == []
