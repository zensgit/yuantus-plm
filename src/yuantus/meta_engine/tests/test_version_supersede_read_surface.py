"""Superseded read-surface: ItemVersion list with B1 lifecycle signals."""

from __future__ import annotations

from datetime import datetime
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.database import get_db
from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.version.service import VersionError, VersionService
from yuantus.meta_engine.web import version_lifecycle_router as lifecycle_module
from yuantus.models import user as _user  # noqa: F401 - registers users table
from yuantus.models.base import Base

import_all_models()


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'supersede-read-surface.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    yield db
    db.close()


def _client(db) -> TestClient:
    app = FastAPI()
    app.include_router(lifecycle_module.version_lifecycle_router, prefix="/api/v1")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[lifecycle_module.get_current_user_id] = lambda: 1
    return TestClient(app)


def _item(session, iid: str) -> Item:
    item = Item(
        id=iid,
        item_type_id="Part",
        config_id=f"cfg-{iid}-{uuid.uuid4()}",
        generation=1,
        is_current=True,
        is_versionable=True,
    )
    session.add(item)
    session.flush()
    return item


def _version(
    session,
    item: Item,
    *,
    vid: str,
    gen: int,
    rev: str,
    released: bool,
    current: bool,
    superseded: bool = False,
    predecessor_id: str | None = None,
    branch: str = "main",
    created_at: datetime | None = None,
) -> ItemVersion:
    version = ItemVersion(
        id=vid,
        item_id=item.id,
        generation=gen,
        revision=rev,
        version_label=f"{gen}.{rev}",
        state="Superseded" if superseded else ("Released" if released else "Draft"),
        is_current=current,
        is_released=released,
        is_superseded=superseded,
        predecessor_id=predecessor_id,
        branch_name=branch,
        created_at=created_at,
        released_at=created_at if released else None,
    )
    session.add(version)
    session.flush()
    if current:
        item.current_version_id = version.id
        session.flush()
    return version


def _seed_status_matrix(session) -> Item:
    item = _item(session, "P")
    v1 = _version(
        session,
        item,
        vid="v-1A",
        gen=1,
        rev="A",
        released=True,
        current=False,
        superseded=True,
        created_at=datetime(2026, 1, 1, 8, 0, 0),
    )
    v2 = _version(
        session,
        item,
        vid="v-1B",
        gen=1,
        rev="B",
        released=True,
        current=False,
        created_at=datetime(2026, 1, 2, 8, 0, 0),
    )
    _version(
        session,
        item,
        vid="v-1C",
        gen=1,
        rev="C",
        released=False,
        current=True,
        predecessor_id=v2.id,
        created_at=datetime(2026, 1, 3, 8, 0, 0),
    )
    _version(
        session,
        item,
        vid="v-branch-draft",
        gen=1,
        rev="D",
        released=False,
        current=False,
        predecessor_id=v1.id,
        branch="feature",
        created_at=datetime(2026, 1, 4, 8, 0, 0),
    )
    session.commit()
    return item


def test_list_versions_surfaces_b1_statuses_and_flags(session):
    _seed_status_matrix(session)

    result = VersionService(session).list_versions("P")

    assert result["item_id"] == "P"
    assert result["is_under_modification"] is True
    rows = {row["version_id"]: row for row in result["versions"]}
    assert rows["v-1A"]["lifecycle_status"] == "historical_released"
    assert rows["v-1A"]["is_superseded"] is True
    assert rows["v-1A"]["state"] == "Superseded"
    assert rows["v-1B"]["lifecycle_status"] == "active_released"
    assert rows["v-1C"]["lifecycle_status"] == "in_work"
    assert rows["v-branch-draft"]["lifecycle_status"] == "draft"


def test_list_versions_uses_stable_generation_created_id_order(session):
    item = _item(session, "P")
    same_time = datetime(2026, 2, 1, 9, 0, 0)
    _version(
        session,
        item,
        vid="v-b",
        gen=2,
        rev="B",
        released=True,
        current=False,
        created_at=same_time,
    )
    _version(
        session,
        item,
        vid="v-a",
        gen=2,
        rev="A",
        released=True,
        current=False,
        created_at=same_time,
    )
    _version(
        session,
        item,
        vid="v-current",
        gen=3,
        rev="A",
        released=True,
        current=True,
        created_at=datetime(2026, 2, 2, 9, 0, 0),
    )
    session.commit()

    assert [
        row["version_id"] for row in VersionService(session).list_versions("P")["versions"]
    ] == ["v-a", "v-b", "v-current"]


def test_list_versions_missing_item_raises_not_found(session):
    with pytest.raises(VersionError, match="not found"):
        VersionService(session).list_versions("missing")


def test_versions_endpoint_serializes_list_and_missing_item_404(session):
    _seed_status_matrix(session)
    client = _client(session)

    response = client.get("/api/v1/versions/items/P/versions")
    assert response.status_code == 200
    payload = response.json()
    assert payload["is_under_modification"] is True
    assert [row["version_id"] for row in payload["versions"]] == [
        "v-1A",
        "v-1B",
        "v-1C",
        "v-branch-draft",
    ]
    assert payload["versions"][0]["lifecycle_status"] == "historical_released"
    assert payload["versions"][2]["lifecycle_status"] == "in_work"

    # D4: v1 has no server-side ?status= filter; undeclared params do not filter.
    unfiltered = client.get("/api/v1/versions/items/P/versions?status=active_released")
    assert unfiltered.status_code == 200
    assert len(unfiltered.json()["versions"]) == 4

    missing = client.get("/api/v1/versions/items/missing/versions")
    assert missing.status_code == 404
