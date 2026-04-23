"""
P2-3.1 PR-2: Dashboard Export — Focused Tests
===============================================
Covers:
  - export_dashboard_items service method (csv + json)
  - same columns as dashboard items
  - same filters passed through
  - HTTP endpoint: route registered, content-type, content-disposition
  - bad format → 400
"""
import pytest
import json
import csv
import io
from unittest.mock import MagicMock, patch
from yuantus.config import get_settings
from yuantus.meta_engine.services.eco_service import ECOApprovalService


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")


def _svc(session):
    svc = ECOApprovalService(session)
    svc.notification_service = MagicMock()
    svc.audit_service = MagicMock()
    return svc


_SAMPLE_ITEMS = [
    {
        "eco_id": "e1", "eco_name": "ECO-1", "eco_state": "progress",
        "stage_id": "s1", "stage_name": "Review", "approval_id": "a1",
        "assignee_id": 10, "assignee_username": "alice",
        "approval_type": "mandatory", "required_role": None,
        "is_overdue": True, "is_escalated": False,
        "approval_deadline": "2026-04-15T10:00:00", "hours_overdue": 5.2,
    },
]


# ========================================================================
# Service: export_dashboard_items
# ========================================================================

class TestExportService:
    def test_json_output_is_valid_json(self):
        session = MagicMock()
        svc = _svc(session)
        svc.get_approval_dashboard_items = MagicMock(return_value=_SAMPLE_ITEMS)
        result = svc.export_dashboard_items(fmt="json")
        parsed = json.loads(result)
        assert len(parsed) == 1
        assert parsed[0]["eco_id"] == "e1"

    def test_csv_output_has_header_and_rows(self):
        session = MagicMock()
        svc = _svc(session)
        svc.get_approval_dashboard_items = MagicMock(return_value=_SAMPLE_ITEMS)
        result = svc.export_dashboard_items(fmt="csv")
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["eco_id"] == "e1"
        assert rows[0]["assignee_username"] == "alice"

    def test_csv_columns_match_export_columns(self):
        session = MagicMock()
        svc = _svc(session)
        svc.get_approval_dashboard_items = MagicMock(return_value=_SAMPLE_ITEMS)
        result = svc.export_dashboard_items(fmt="csv")
        reader = csv.DictReader(io.StringIO(result))
        assert reader.fieldnames == ECOApprovalService._EXPORT_COLUMNS

    def test_export_passes_filters_to_items(self):
        session = MagicMock()
        svc = _svc(session)
        svc.get_approval_dashboard_items = MagicMock(return_value=[])
        svc.export_dashboard_items(
            fmt="json", company_id="acme", status_filter="overdue",
        )
        kw = svc.get_approval_dashboard_items.call_args[1]
        assert kw["company_id"] == "acme"
        assert kw["status_filter"] == "overdue"

    def test_empty_items_produces_csv_header_only(self):
        session = MagicMock()
        svc = _svc(session)
        svc.get_approval_dashboard_items = MagicMock(return_value=[])
        result = svc.export_dashboard_items(fmt="csv")
        lines = result.strip().split("\n")
        assert len(lines) == 1  # header only
        assert "eco_id" in lines[0]

    def test_empty_items_produces_json_empty_array(self):
        session = MagicMock()
        svc = _svc(session)
        svc.get_approval_dashboard_items = MagicMock(return_value=[])
        result = svc.export_dashboard_items(fmt="json")
        assert json.loads(result) == []


# ========================================================================
# HTTP endpoint
# ========================================================================

class TestExportHTTP:
    def _client(self):
        from fastapi.testclient import TestClient
        from yuantus.api.app import create_app
        from yuantus.database import get_db
        app = create_app()
        db = MagicMock()
        def override():
            try: yield db
            finally: pass
        app.dependency_overrides[get_db] = override
        return TestClient(app), db

    def test_route_registered(self):
        from yuantus.api.app import create_app
        app = create_app()
        paths = {r.path for r in app.routes}
        assert "/api/v1/eco/approvals/dashboard/export" in paths

    def test_json_export_200(self):
        client, db = self._client()
        with patch("yuantus.meta_engine.web.eco_approval_ops_router.ECOApprovalService") as M:
            M.return_value.export_dashboard_items.return_value = json.dumps(_SAMPLE_ITEMS)
            resp = client.get("/api/v1/eco/approvals/dashboard/export?fmt=json")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_csv_export_200(self):
        client, db = self._client()
        with patch("yuantus.meta_engine.web.eco_approval_ops_router.ECOApprovalService") as M:
            M.return_value.export_dashboard_items.return_value = "eco_id,eco_name\ne1,ECO-1\n"
            resp = client.get("/api/v1/eco/approvals/dashboard/export?fmt=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "approval_dashboard.csv" in resp.headers.get("content-disposition", "")

    def test_bad_format_400(self):
        client, db = self._client()
        resp = client.get("/api/v1/eco/approvals/dashboard/export?fmt=xml")
        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]

    def test_filters_forwarded(self):
        client, db = self._client()
        with patch("yuantus.meta_engine.web.eco_approval_ops_router.ECOApprovalService") as M:
            M.return_value.export_dashboard_items.return_value = "[]"
            client.get(
                "/api/v1/eco/approvals/dashboard/export"
                "?fmt=json&company_id=acme&status=overdue"
            )
        kw = M.return_value.export_dashboard_items.call_args[1]
        assert kw["company_id"] == "acme"
        assert kw["status_filter"] == "overdue"
