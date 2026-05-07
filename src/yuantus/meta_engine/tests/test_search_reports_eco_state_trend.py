from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.services.search_service import SearchService
from yuantus.meta_engine.web.search_router import search_router


TREND_REPORT = {
    "engine": "db",
    "trend_source": "created_at_current_state",
    "days": 7,
    "start_date": "2026-05-01",
    "end_date": "2026-05-07",
    "buckets": [
        {"date": "2026-05-06", "state": "draft", "count": 2},
        {"date": "2026-05-07", "state": "approved", "count": 1},
    ],
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


def _rows_result(rows: list[tuple[object, object]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def test_eco_state_trend_report_returns_zero_buckets_without_db_session() -> None:
    now = datetime(2026, 5, 7, 12, tzinfo=timezone.utc)
    service = SearchService(session=None)

    assert service.eco_state_trend_report(days=7, now=now) == {
        "engine": "db",
        "trend_source": "created_at_current_state",
        "days": 7,
        "start_date": "2026-05-01",
        "end_date": "2026-05-07",
        "buckets": [],
    }


def test_eco_state_trend_report_groups_by_created_date_and_current_state() -> None:
    session = MagicMock()
    now = datetime(2026, 5, 7, 12, tzinfo=timezone.utc)
    session.execute.return_value = _rows_result(
        [
            ("draft", datetime(2026, 5, 6, 10, tzinfo=timezone.utc)),
            ("draft", datetime(2026, 5, 6, 11, tzinfo=timezone.utc)),
            ("approved", datetime(2026, 5, 7, 1, tzinfo=timezone.utc)),
        ]
    )
    service = SearchService(session)

    assert service.eco_state_trend_report(days=7, now=now) == TREND_REPORT


def test_eco_state_trend_report_normalizes_unknown_state_and_naive_datetimes() -> None:
    session = MagicMock()
    now = datetime(2026, 5, 7, 12, tzinfo=timezone.utc)
    session.execute.return_value = _rows_result(
        [
            (None, datetime(2026, 5, 7, 9)),
            ("", datetime(2026, 5, 7, 10)),
        ]
    )
    service = SearchService(session)

    assert service.eco_state_trend_report(days=1, now=now) == {
        "engine": "db",
        "trend_source": "created_at_current_state",
        "days": 1,
        "start_date": "2026-05-07",
        "end_date": "2026-05-07",
        "buckets": [
            {"date": "2026-05-07", "state": "unknown", "count": 2},
        ],
    }


def test_search_eco_state_trend_endpoint_requires_admin() -> None:
    client = _client(_current_user(roles=["viewer"]))

    response = client.get("/api/v1/search/reports/eco-state-trend")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_search_eco_state_trend_endpoint_returns_json_for_admin() -> None:
    client = _client(_current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.eco_state_trend_report.return_value = TREND_REPORT
        response = client.get("/api/v1/search/reports/eco-state-trend?days=7")

    assert response.status_code == 200
    assert response.json() == TREND_REPORT
    service_cls.return_value.eco_state_trend_report.assert_called_once_with(days=7)


def test_search_eco_state_trend_endpoint_exports_csv_for_admin() -> None:
    client = _client(_current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.eco_state_trend_report.return_value = TREND_REPORT
        response = client.get("/api/v1/search/reports/eco-state-trend?days=7&format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines() == [
        "date,state,count",
        "2026-05-06,draft,2",
        "2026-05-07,approved,1",
    ]


def test_search_eco_state_trend_endpoint_rejects_unbounded_days() -> None:
    client = _client(_current_user(roles=["admin"]))

    response = client.get("/api/v1/search/reports/eco-state-trend?days=367")

    assert response.status_code == 422


def test_search_eco_state_trend_route_registered_once_and_owned_by_search_router() -> None:
    app = create_app()

    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/search/reports/eco-state-trend"
        and "GET" in getattr(route, "methods", set())
    ]

    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "yuantus.meta_engine.web.search_router"
