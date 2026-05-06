from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.meta_engine.events.domain_events import ItemCreatedEvent
from yuantus.meta_engine.services import search_indexer
from yuantus.meta_engine.web.search_router import search_router


EXPECTED_HANDLERS = [
    "item.created",
    "item.updated",
    "item.state_changed",
    "item.deleted",
    "eco.created",
    "eco.updated",
    "eco.deleted",
]


def _current_user(*, roles: list[str], is_superuser: bool = False) -> CurrentUser:
    return CurrentUser(
        id=1,
        tenant_id="tenant-1",
        org_id="org-1",
        username="tester",
        email="tester@example.com",
        roles=roles,
        is_superuser=is_superuser,
    )


def _client(user: CurrentUser) -> TestClient:
    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app)


def test_search_indexer_status_lists_incremental_event_handlers() -> None:
    status = search_indexer.indexer_status()

    assert status["handlers"] == EXPECTED_HANDLERS
    assert set(status["event_counts"]) == set(EXPECTED_HANDLERS)
    assert all(isinstance(value, int) for value in status["event_counts"].values())


def test_item_created_handler_updates_runtime_status(monkeypatch) -> None:
    before = search_indexer.indexer_status()["event_counts"]["item.created"]
    indexed_item_ids: list[str] = []

    class FakeSession:
        def get(self, _model, item_id: str):
            return SimpleNamespace(id=item_id)

    class FakeSearchService:
        def __init__(self, session):
            self.session = session
            self.client = object()

        def ensure_index(self) -> None:
            return None

        def index_item(self, item) -> None:
            indexed_item_ids.append(item.id)

    @contextmanager
    def fake_db_session():
        yield FakeSession()

    monkeypatch.setattr(search_indexer, "SearchService", FakeSearchService)
    monkeypatch.setattr(search_indexer, "get_db_session", fake_db_session)

    search_indexer._handle_item_created(
        ItemCreatedEvent(item_id="item-123", item_type_id="Part", properties={})
    )

    status = search_indexer.indexer_status()
    assert status["event_counts"]["item.created"] == before + 1
    assert status["last_event_type"] == "item.created"
    assert status["last_success_event_type"] == "item.created"
    assert indexed_item_ids == ["item-123"]


def test_handler_error_status_is_redacted(monkeypatch) -> None:
    class FakeSession:
        def get(self, _model, item_id: str):
            return SimpleNamespace(id=item_id)

    class FakeSearchService:
        def __init__(self, session):
            self.session = session
            self.client = object()

        def ensure_index(self) -> None:
            return None

        def index_item(self, _item) -> None:
            raise RuntimeError(
                "failed postgresql://app:supersecret@example/db password=hidden token=abc"
            )

    @contextmanager
    def fake_db_session():
        yield FakeSession()

    monkeypatch.setattr(search_indexer, "SearchService", FakeSearchService)
    monkeypatch.setattr(search_indexer, "get_db_session", fake_db_session)

    search_indexer._handle_item_created(
        ItemCreatedEvent(item_id="item-456", item_type_id="Part", properties={})
    )

    status = search_indexer.indexer_status()
    assert status["last_error_event_type"] == "item.created"
    assert status["last_error"].startswith("RuntimeError: ")
    assert "supersecret" not in status["last_error"]
    assert "hidden" not in status["last_error"]
    assert "abc" not in status["last_error"]
    assert "password=***" in status["last_error"]
    assert "token=***" in status["last_error"]


def test_search_indexer_status_endpoint_requires_admin() -> None:
    client = _client(_current_user(roles=["viewer"]))

    response = client.get("/api/v1/search/indexer/status")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_search_indexer_status_endpoint_returns_status_for_admin() -> None:
    client = _client(_current_user(roles=["admin"]))

    response = client.get("/api/v1/search/indexer/status")

    assert response.status_code == 200
    body = response.json()
    assert body["handlers"] == EXPECTED_HANDLERS
    assert set(body["event_counts"]) == set(EXPECTED_HANDLERS)
    assert isinstance(body["registered"], bool)


def test_search_indexer_status_route_registered_once_and_owned_by_search_router() -> None:
    app = create_app()

    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/search/indexer/status"
        and "GET" in getattr(route, "methods", set())
    ]

    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "yuantus.meta_engine.web.search_router"
