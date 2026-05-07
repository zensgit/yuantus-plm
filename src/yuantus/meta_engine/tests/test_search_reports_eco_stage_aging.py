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


AGING_REPORT = {
    "engine": "db",
    "age_source": "updated_at_or_created_at",
    "buckets": [
        {"key": "review", "count": 2, "avg_age_days": 3.0, "max_age_days": 5.0},
        {"key": "unknown", "count": 1, "avg_age_days": 0.0, "max_age_days": 0.0},
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


def _rows_result(rows: list[tuple[object, object, object]]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def test_eco_stage_aging_report_returns_zero_buckets_without_db_session() -> None:
    service = SearchService(session=None)

    assert service.eco_stage_aging_report() == {
        "engine": "db",
        "age_source": "updated_at_or_created_at",
        "buckets": [],
    }


def test_eco_stage_aging_report_groups_by_stage_and_updated_age() -> None:
    session = MagicMock()
    now = datetime(2026, 5, 7, tzinfo=timezone.utc)
    session.execute.return_value = _rows_result(
        [
            ("review", datetime(2026, 5, 2, tzinfo=timezone.utc), None),
            ("review", datetime(2026, 5, 6, tzinfo=timezone.utc), None),
            ("draft", datetime(2026, 5, 4, tzinfo=timezone.utc), None),
        ]
    )
    service = SearchService(session)

    assert service.eco_stage_aging_report(now=now) == {
        "engine": "db",
        "age_source": "updated_at_or_created_at",
        "buckets": [
            {
                "key": "review",
                "count": 2,
                "avg_age_days": 3.0,
                "max_age_days": 5.0,
            },
            {
                "key": "draft",
                "count": 1,
                "avg_age_days": 3.0,
                "max_age_days": 3.0,
            },
        ],
    }


def test_eco_stage_aging_report_falls_back_to_created_at_and_unknown_stage() -> None:
    session = MagicMock()
    now = datetime(2026, 5, 7, tzinfo=timezone.utc)
    session.execute.return_value = _rows_result(
        [
            (None, None, datetime(2026, 5, 5, tzinfo=timezone.utc)),
            ("", None, None),
        ]
    )
    service = SearchService(session)

    assert service.eco_stage_aging_report(now=now) == {
        "engine": "db",
        "age_source": "updated_at_or_created_at",
        "buckets": [
            {
                "key": "unknown",
                "count": 2,
                "avg_age_days": 1.0,
                "max_age_days": 2.0,
            },
        ],
    }


def test_search_eco_stage_aging_endpoint_requires_admin() -> None:
    client = _client(_current_user(roles=["viewer"]))

    response = client.get("/api/v1/search/reports/eco-stage-aging")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_search_eco_stage_aging_endpoint_returns_json_for_admin() -> None:
    client = _client(_current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.eco_stage_aging_report.return_value = AGING_REPORT
        response = client.get("/api/v1/search/reports/eco-stage-aging")

    assert response.status_code == 200
    assert response.json() == AGING_REPORT


def test_search_eco_stage_aging_endpoint_exports_csv_for_admin() -> None:
    client = _client(_current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.eco_stage_aging_report.return_value = AGING_REPORT
        response = client.get("/api/v1/search/reports/eco-stage-aging?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.text.splitlines() == [
        "stage,count,avg_age_days,max_age_days",
        "review,2,3.0,5.0",
        "unknown,1,0.0,0.0",
    ]


def test_search_eco_stage_aging_route_registered_once_and_owned_by_search_router() -> None:
    app = create_app()

    matches = [
        route
        for route in app.routes
        if getattr(route, "path", None) == "/api/v1/search/reports/eco-stage-aging"
        and "GET" in getattr(route, "methods", set())
    ]

    assert len(matches) == 1
    assert matches[0].endpoint.__module__ == "yuantus.meta_engine.web.search_router"
