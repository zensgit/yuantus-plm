from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.web.search_router import (
    SearchEcoStageAgingResponse,
    SearchEcoStateTrendResponse,
    SearchReportsSummaryResponse,
    search_router,
)


EXPECTED_SEARCH_REPORT_ROUTES = {
    ("GET", "/api/v1/search/reports/summary"),
    ("GET", "/api/v1/search/reports/eco-stage-aging"),
    ("GET", "/api/v1/search/reports/eco-state-trend"),
}
EXPECTED_OWNER_MODULE = "yuantus.meta_engine.web.search_router"


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


def _search_report_routes() -> dict[tuple[str, str], str]:
    routes: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api/v1/search/reports/"):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            routes[(method, route.path)] = route.endpoint.__module__
    return routes


def test_search_reports_public_route_surface_is_pinned() -> None:
    routes = _search_report_routes()

    assert set(routes) == EXPECTED_SEARCH_REPORT_ROUTES
    assert set(routes.values()) == {EXPECTED_OWNER_MODULE}


def test_search_reports_routes_are_registered_exactly_once() -> None:
    counts: dict[tuple[str, str], int] = {route: 0 for route in EXPECTED_SEARCH_REPORT_ROUTES}
    for route in create_app().routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods or set():
            key = (method, route.path)
            if key in counts:
                counts[key] += 1

    assert counts == {route: 1 for route in EXPECTED_SEARCH_REPORT_ROUTES}


def test_search_reports_routes_require_admin_user() -> None:
    client = _client(_current_user(roles=["viewer"]))

    for _, path in sorted(EXPECTED_SEARCH_REPORT_ROUTES):
        response = client.get(path)
        assert response.status_code == 403
        assert response.json()["detail"] == "Admin role required"


def test_search_reports_response_model_field_sets_are_pinned() -> None:
    assert set(SearchReportsSummaryResponse.model_fields) == {"engine", "items", "ecos"}
    assert set(SearchEcoStageAgingResponse.model_fields) == {
        "engine",
        "age_source",
        "buckets",
    }
    assert set(SearchEcoStateTrendResponse.model_fields) == {
        "engine",
        "trend_source",
        "days",
        "start_date",
        "end_date",
        "buckets",
    }


def test_search_reports_csv_headers_are_pinned() -> None:
    client = _client(_current_user(roles=["admin"]))

    with patch("yuantus.meta_engine.web.search_router.SearchService") as service_cls:
        service_cls.return_value.reports_summary.return_value = {
            "engine": "db",
            "items": {"total": 0, "by_item_type": [], "by_state": []},
            "ecos": {"total": 0, "by_state": [], "by_stage": []},
        }
        service_cls.return_value.eco_stage_aging_report.return_value = {
            "engine": "db",
            "age_source": "updated_at_or_created_at",
            "buckets": [],
        }
        service_cls.return_value.eco_state_trend_report.return_value = {
            "engine": "db",
            "trend_source": "created_at_current_state",
            "days": 30,
            "start_date": "2026-04-08",
            "end_date": "2026-05-07",
            "buckets": [],
        }

        assert client.get("/api/v1/search/reports/summary?format=csv").text.splitlines()[0] == (
            "section,key,count"
        )
        assert client.get("/api/v1/search/reports/eco-stage-aging?format=csv").text.splitlines()[0] == (
            "stage,count,avg_age_days,max_age_days"
        )
        assert client.get("/api/v1/search/reports/eco-state-trend?format=csv").text.splitlines()[0] == (
            "date,state,count"
        )


def test_runtime_runbook_documents_search_reports_surface() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    runbook = (repo_root / "docs" / "RUNBOOK_RUNTIME.md").read_text(encoding="utf-8")

    required_snippets = [
        "### Search reports",
        "GET /api/v1/search/reports/summary",
        "GET /api/v1/search/reports/eco-stage-aging",
        "GET /api/v1/search/reports/eco-state-trend",
        "section,key,count",
        "stage,count,avg_age_days,max_age_days",
        "date,state,count",
        "Admin role required",
        "created_at_current_state",
        "not state-transition history",
    ]
    for snippet in required_snippets:
        assert snippet in runbook
