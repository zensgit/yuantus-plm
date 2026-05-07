from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.search_service import SearchService
from yuantus.meta_engine.web.search_router import search_router


SUMMARY = {
    "engine": "db",
    "items": {
        "total": 3,
        "by_item_type": [
            {"key": "Part", "count": 2},
            {"key": "Document", "count": 1},
        ],
        "by_state": [
            {"key": "released", "count": 2},
            {"key": "unknown", "count": 1},
        ],
    },
    "ecos": {
        "total": 2,
        "by_state": [{"key": "draft", "count": 2}],
        "by_stage": [{"key": "review", "count": 2}],
    },
}


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
    mock_db = MagicMock()

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _scalar_result(value: int) -> MagicMock:
    result = MagicMock()
    result.scalar.return_value = value
    return result


def _rows_result(rows: list[tuple[object, int]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def test_reports_summary_returns_zero_buckets_without_db_session() -> None:
    service = SearchService(session=None)

    assert service.reports_summary() == {
        "engine": "db",
        "items": {"total": 0, "by_item_type": [], "by_state": []},
        "ecos": {"total": 0, "by_state": [], "by_stage": []},
    }


def test_reports_summary_aggregates_items_and_ecos_from_db_session() -> None:
    session = MagicMock()
    session.execute.side_effect = [
        _scalar_result(3),
        _rows_result([("Part", 2), ("Document", 1)]),
        _rows_result([("released", 2), (None, 1)]),
        _scalar_result(2),
        _rows_result([("draft", 2)]),
        _rows_result([("review", 2)]),
    ]
    service = SearchService(session)

    assert service.reports_summary() == SUMMARY


def test_search_reports_summary_endpoint_requires_admin() -> None:
    client = _client(_current_user(roles=["viewer"]))

    response = client.get("/api/v1/search/reports/summary")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_search_reports_summary_endpoint_returns_json_for_admin() -> None:
    client = _client(_current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.reports_summary.return_value = SUMMARY
        response = client.get("/api/v1/search/reports/summary")

    assert response.status_code == 200
    assert response.json() == SUMMARY


def test_search_reports_summary_endpoint_exports_csv_for_admin() -> None:
    client = _client(_current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.reports_summary.return_value = SUMMARY
        response = client.get("/api/v1/search/reports/summary?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines() == [
        "section,key,count",
        "items.total,total,3",
        "items.by_item_type,Part,2",
        "items.by_item_type,Document,1",
        "items.by_state,released,2",
        "items.by_state,unknown,1",
        "ecos.total,total,2",
        "ecos.by_state,draft,2",
        "ecos.by_stage,review,2",
    ]


def test_search_reports_summary_route_registered_once_and_owned_by_search_router() -> None:
    app = create_app()

    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/search/reports/summary"
        and "GET" in getattr(route, "methods", set())
    ]

    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "yuantus.meta_engine.web.search_router"
