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

    assert status["status_started_at"].endswith("Z")
    assert isinstance(status["uptime_seconds"], int)
    assert status["uptime_seconds"] >= 0
    assert status["health"] in {"ok", "not_registered", "degraded"}
    assert isinstance(status["health_reasons"], list)
    assert status["handlers"] == EXPECTED_HANDLERS
    assert set(status["subscription_counts"]) == set(EXPECTED_HANDLERS)
    assert isinstance(status["missing_handlers"], list)
    assert isinstance(status["duplicate_handlers"], list)
    assert set(status["event_counts"]) == set(EXPECTED_HANDLERS)
    assert set(status["success_counts"]) == set(EXPECTED_HANDLERS)
    assert set(status["skipped_counts"]) == set(EXPECTED_HANDLERS)
    assert set(status["error_counts"]) == set(EXPECTED_HANDLERS)
    assert all(isinstance(value, int) for value in status["event_counts"].values())
    assert all(isinstance(value, int) for value in status["subscription_counts"].values())
    assert all(isinstance(value, int) for value in status["success_counts"].values())
    assert all(isinstance(value, int) for value in status["skipped_counts"].values())
    assert all(isinstance(value, int) for value in status["error_counts"].values())
    for field in (
        "last_event_age_seconds",
        "last_success_age_seconds",
        "last_skipped_age_seconds",
        "last_error_age_seconds",
    ):
        assert field in status
        assert status[field] is None or status[field] >= 0


def test_register_search_index_handlers_records_expected_subscriptions() -> None:
    search_indexer.register_search_index_handlers()

    status = search_indexer.indexer_status()
    assert status["registered"] is True
    assert status["registered_at"].endswith("Z")
    assert status["health"] == "ok"
    assert status["health_reasons"] == []
    assert status["missing_handlers"] == []
    assert status["duplicate_handlers"] == []
    assert status["subscription_counts"] == {
        event_type: 1 for event_type in EXPECTED_HANDLERS
    }


def test_indexer_health_reports_registration_and_subscription_anomalies(monkeypatch) -> None:
    subscription_counts = {event_type: 1 for event_type in EXPECTED_HANDLERS}
    subscription_counts["item.created"] = 0
    subscription_counts["eco.deleted"] = 2
    monkeypatch.setattr(search_indexer, "_REGISTERED", True)
    monkeypatch.setattr(search_indexer, "_subscription_counts", lambda: subscription_counts)

    status = search_indexer.indexer_status()

    assert status["health"] == "degraded"
    assert status["health_reasons"] == ["missing-handlers", "duplicate-handlers"]
    assert status["missing_handlers"] == ["item.created"]
    assert status["duplicate_handlers"] == ["eco.deleted"]


def test_indexer_health_reports_not_registered(monkeypatch) -> None:
    monkeypatch.setattr(search_indexer, "_REGISTERED", False)
    monkeypatch.setattr(
        search_indexer,
        "_subscription_counts",
        lambda: {event_type: 0 for event_type in EXPECTED_HANDLERS},
    )

    status = search_indexer.indexer_status()

    assert status["health"] == "degraded"
    assert status["health_reasons"] == ["not-registered", "missing-handlers"]


def test_item_created_handler_updates_runtime_status(monkeypatch) -> None:
    before_status = search_indexer.indexer_status()
    event_count_before = before_status["event_counts"]["item.created"]
    success_count_before = before_status["success_counts"]["item.created"]
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
    assert status["event_counts"]["item.created"] == event_count_before + 1
    assert status["success_counts"]["item.created"] == success_count_before + 1
    assert status["last_event_type"] == "item.created"
    assert status["last_event_at"].endswith("Z")
    assert 0 <= status["last_event_age_seconds"] <= 10
    assert status["last_outcome"] == "success"
    assert status["last_success_event_type"] == "item.created"
    assert status["last_success_at"].endswith("Z")
    assert 0 <= status["last_success_age_seconds"] <= 10
    assert indexed_item_ids == ["item-123"]


def test_handler_skip_updates_outcome_counts(monkeypatch) -> None:
    before_status = search_indexer.indexer_status()
    event_count_before = before_status["event_counts"]["item.created"]
    skipped_count_before = before_status["skipped_counts"]["item.created"]

    class FakeSession:
        def get(self, _model, item_id: str):
            return SimpleNamespace(id=item_id)

    class FakeSearchService:
        def __init__(self, session):
            self.session = session
            self.client = None

    @contextmanager
    def fake_db_session():
        yield FakeSession()

    monkeypatch.setattr(search_indexer, "SearchService", FakeSearchService)
    monkeypatch.setattr(search_indexer, "get_db_session", fake_db_session)

    search_indexer._handle_item_created(
        ItemCreatedEvent(item_id="item-disabled", item_type_id="Part", properties={})
    )

    status = search_indexer.indexer_status()
    assert status["event_counts"]["item.created"] == event_count_before + 1
    assert status["skipped_counts"]["item.created"] == skipped_count_before + 1
    assert status["last_event_type"] == "item.created"
    assert status["last_event_at"].endswith("Z")
    assert 0 <= status["last_event_age_seconds"] <= 10
    assert status["last_outcome"] == "skipped"
    assert status["last_skipped_event_type"] == "item.created"
    assert status["last_skipped_at"].endswith("Z")
    assert 0 <= status["last_skipped_age_seconds"] <= 10
    assert status["last_skipped_reason"] == "search-engine-disabled"


def test_handler_error_status_is_redacted(monkeypatch) -> None:
    error_count_before = search_indexer.indexer_status()["error_counts"]["item.created"]

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
    assert status["error_counts"]["item.created"] == error_count_before + 1
    assert status["last_outcome"] == "error"
    assert status["last_error_event_type"] == "item.created"
    assert status["last_error_at"].endswith("Z")
    assert 0 <= status["last_error_age_seconds"] <= 10
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
    assert body["status_started_at"].endswith("Z")
    assert isinstance(body["uptime_seconds"], int)
    assert body["health"] in {"ok", "not_registered", "degraded"}
    assert isinstance(body["health_reasons"], list)
    assert body["handlers"] == EXPECTED_HANDLERS
    assert set(body["subscription_counts"]) == set(EXPECTED_HANDLERS)
    assert isinstance(body["missing_handlers"], list)
    assert isinstance(body["duplicate_handlers"], list)
    assert set(body["event_counts"]) == set(EXPECTED_HANDLERS)
    assert set(body["success_counts"]) == set(EXPECTED_HANDLERS)
    assert set(body["skipped_counts"]) == set(EXPECTED_HANDLERS)
    assert set(body["error_counts"]) == set(EXPECTED_HANDLERS)
    assert isinstance(body["registered"], bool)
    for field in (
        "last_event_age_seconds",
        "last_success_age_seconds",
        "last_skipped_age_seconds",
        "last_error_age_seconds",
    ):
        assert field in body
        assert body[field] is None or body[field] >= 0


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
