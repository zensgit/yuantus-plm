"""A3 workstation checkout context contracts."""
from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.file_service import VersionFileError, VersionFileService
from yuantus.meta_engine.version.models import ItemVersion, VersionFile
from yuantus.meta_engine.version.service import VersionError, VersionService
from yuantus.meta_engine.web import cad_checkin_router
from yuantus.models import user as _user  # noqa: F401 - registers users table
from yuantus.models.base import Base

import_all_models()


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'a3-checkout-context.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    yield db
    db.close()


def _item_with_version(session, item_id: str = "P") -> tuple[Item, ItemVersion]:
    item = Item(
        id=item_id,
        item_type_id="Part",
        config_id=f"cfg-{item_id}-{uuid.uuid4()}",
        generation=1,
        is_current=True,
        state="Active",
    )
    session.add(item)
    version = ItemVersion(
        id=f"v-{uuid.uuid4()}",
        item_id=item.id,
        generation=1,
        revision="A",
        version_label="1.A",
        state="Draft",
        is_current=True,
        is_released=False,
    )
    session.add(version)
    session.flush()
    item.current_version_id = version.id
    session.flush()
    return item, version


def _version_file(session, version: ItemVersion) -> VersionFile:
    file = FileContainer(
        id=f"f-{uuid.uuid4()}",
        filename="part.step",
        file_type="step",
        system_path="/vault/part.step",
    )
    session.add(file)
    vf = VersionFile(
        id=f"vf-{uuid.uuid4()}",
        version_id=version.id,
        file_id=file.id,
        file_role="native_cad",
        sequence=0,
    )
    session.add(vf)
    session.flush()
    return vf


def test_version_checkout_records_context_and_rejects_same_user_different_workspace(session):
    item, version = _item_with_version(session)
    service = VersionService(session)

    checked_out = service.checkout(
        item.id,
        7,
        client_host="ws-1",
        client_workspace_path="C:/cad/P",
        client_info={"source": "pytest"},
    )

    assert checked_out.id == version.id
    assert checked_out.checkout_client_host == "ws-1"
    assert checked_out.checkout_workspace_path == "C:/cad/P"
    assert checked_out.checkout_client_info == {"source": "pytest"}

    same = service.checkout(
        item.id,
        7,
        client_host="ws-1",
        client_workspace_path="C:/cad/P",
    )
    assert same.id == version.id

    # Legacy callers that send no context remain idempotent for the same user.
    assert service.checkout(item.id, 7).id == version.id

    with pytest.raises(VersionError, match="different workstation"):
        service.checkout(
            item.id,
            7,
            client_host="ws-2",
            client_workspace_path="D:/other/P",
        )


def test_version_checkin_clears_context(session):
    item, version = _item_with_version(session)
    service = VersionService(session)
    service.checkout(
        item.id,
        7,
        client_host="ws-1",
        client_workspace_path="C:/cad/P",
    )

    service.checkin(item.id, 7)

    assert version.checked_out_by_id is None
    assert version.checkout_client_host is None
    assert version.checkout_workspace_path is None
    assert version.checkout_client_info is None


def test_file_checkout_records_returns_rejects_and_clears_context(session):
    _item, version = _item_with_version(session)
    vf = _version_file(session, version)
    service = VersionFileService(session)

    service.checkout_file(
        version.id,
        vf.file_id,
        7,
        file_role="native_cad",
        client_host="ws-1",
        client_workspace_path="C:/cad/P",
        client_info={"source": "pytest"},
    )
    lock = service.get_file_lock(version.id, vf.file_id, file_role="native_cad")

    assert lock["lock_context"] == {
        "client_host": "ws-1",
        "workspace_path": "C:/cad/P",
        "client_info": {"source": "pytest"},
    }
    with pytest.raises(VersionFileError, match="different workstation"):
        service.checkout_file(
            version.id,
            vf.file_id,
            7,
            file_role="native_cad",
            client_host="ws-2",
            client_workspace_path="D:/other/P",
        )

    service.undo_checkout_file(version.id, vf.file_id, 7, file_role="native_cad")
    lock = service.get_file_lock(version.id, vf.file_id, file_role="native_cad")
    assert lock["checked_out_by_id"] is None
    assert lock["lock_context"] == {
        "client_host": None,
        "workspace_path": None,
        "client_info": None,
    }


def test_cad_checkout_router_passes_context_and_returns_lock_context():
    session = SimpleNamespace(commit=lambda: None, rollback=lambda: None)

    class Manager:
        def __init__(self) -> None:
            self.session = session
            self.kwargs = None

        def checkout(self, item_id: str, **kwargs):
            self.kwargs = {"item_id": item_id, **kwargs}
            return SimpleNamespace(
                id="ver-1",
                checked_out_by_id=7,
                checkout_client_host=kwargs["client_host"],
                checkout_workspace_path=kwargs["client_workspace_path"],
                checkout_client_info=kwargs["client_info"],
            )

    manager = Manager()
    result = cad_checkin_router.checkout_document(
        "P",
        payload={
            "client_host": "ws-1",
            "client_workspace_path": "C:/cad/P",
            "client_info": {"source": "pytest"},
        },
        mgr=manager,
    )

    assert manager.kwargs == {
        "item_id": "P",
        "client_host": "ws-1",
        "client_workspace_path": "C:/cad/P",
        "client_info": {"source": "pytest"},
    }
    assert result["checked_out_by_id"] == 7
    assert result["locked_by_id"] == 7
    assert result["lock_context"] == {
        "client_host": "ws-1",
        "workspace_path": "C:/cad/P",
        "client_info": {"source": "pytest"},
    }


def test_cad_checkout_router_maps_context_conflict_to_409():
    session = SimpleNamespace(commit=lambda: None, rollback=lambda: None)

    class Manager:
        def __init__(self) -> None:
            self.session = session

        def checkout(self, *_args, **_kwargs):
            raise VersionError("Version is already checked out by this user from a different workstation")

    with pytest.raises(HTTPException) as exc_info:
        cad_checkin_router.checkout_document(
            "P",
            payload={"client_host": "ws-2", "client_workspace_path": "D:/other/P"},
            mgr=Manager(),
        )

    assert exc_info.value.status_code == 409


def test_a3_model_and_migration_columns_stay_in_lockstep():
    expected = {
        "checkout_client_host",
        "checkout_workspace_path",
        "checkout_client_info",
    }
    assert expected.issubset(ItemVersion.__table__.columns.keys())
    assert expected.issubset(VersionFile.__table__.columns.keys())

    migration = Path(
        "migrations/versions/"
        "a3_checkout_context_001_add_workstation_checkout_context.py"
    ).read_text(encoding="utf-8")
    for name in expected:
        assert name in migration
    assert 'down_revision: Union[str, None] = "b1_supersede_001"' in migration
