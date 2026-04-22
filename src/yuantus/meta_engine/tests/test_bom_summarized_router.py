from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db

import pytest

from yuantus.config import get_settings


@pytest.fixture(autouse=True)
def _disable_auth_enforcement_for_router_unit_tests(monkeypatch):
    """These tests override router dependencies; middleware auth is out of scope."""
    monkeypatch.setattr(get_settings(), "AUTH_MODE", "optional")




def _client_with_user(user):
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), mock_db_session


def _sample_compare_result():
    return {
        "summary": {
            "added": 1,
            "removed": 1,
            "changed": 1,
            "changed_major": 1,
            "changed_minor": 0,
            "changed_info": 0,
        },
        "added": [
            {
                "line_key": "line-add",
                "parent_id": "p-1",
                "child_id": "c-1",
                "relationship_id": "rel-add",
                "properties": {"quantity": 3, "uom": "EA"},
            }
        ],
        "removed": [
            {
                "line_key": "line-remove",
                "parent_id": "p-2",
                "child_id": "c-2",
                "relationship_id": "rel-remove",
                "properties": {"quantity": 2, "uom": "EA"},
            }
        ],
        "changed": [
            {
                "line_key": "line-change",
                "parent_id": "p-3",
                "child_id": "c-3",
                "relationship_id": "rel-change",
                "severity": "major",
                "before": {"quantity": 1, "uom": "EA"},
                "after": {"quantity": 4, "uom": "EA"},
                "changes": [{"field": "quantity", "left": 1, "right": 4, "severity": "major"}],
            }
        ],
    }


def test_compare_bom_summarized_transforms_rows_and_defaults_to_summarized_mode():
    user = SimpleNamespace(id=301, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)
    compare_mock = AsyncMock(return_value=_sample_compare_result())

    with patch("yuantus.meta_engine.web.bom_compare_router.compare_bom", new=compare_mock):
        response = client.get(
            "/api/v1/bom/compare/summarized"
            "?left_type=item&left_id=i-left"
            "&right_type=item&right_id=i-right"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 3
    assert payload["summary"]["total_rows"] == 3
    assert payload["summary"]["added"] == 1
    assert payload["summary"]["removed"] == 1
    assert payload["summary"]["changed"] == 1
    assert payload["summary"]["changed_major"] == 1
    assert payload["summary"]["quantity_delta_total"] == pytest.approx(4.0)

    rows = payload["rows"]
    assert [row["status"] for row in rows] == ["added", "removed", "changed"]
    assert rows[0]["quantity_before"] is None
    assert rows[0]["quantity_after"] == pytest.approx(3.0)
    assert rows[0]["quantity_delta"] == pytest.approx(3.0)
    assert rows[1]["quantity_before"] == pytest.approx(2.0)
    assert rows[1]["quantity_after"] is None
    assert rows[1]["quantity_delta"] == pytest.approx(-2.0)
    assert rows[2]["quantity_before"] == pytest.approx(1.0)
    assert rows[2]["quantity_after"] == pytest.approx(4.0)
    assert rows[2]["quantity_delta"] == pytest.approx(3.0)
    assert rows[2]["severity"] == "major"
    assert rows[2]["change_fields"] == ["quantity"]

    assert compare_mock.await_count == 1
    assert compare_mock.await_args.kwargs["compare_mode"] == "summarized"


def test_compare_bom_summarized_export_csv():
    user = SimpleNamespace(id=302, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.bom_compare_router.compare_bom",
        new=AsyncMock(return_value=_sample_compare_result()),
    ):
        response = client.get(
            "/api/v1/bom/compare/summarized/export"
            "?left_type=item&left_id=i-left"
            "&right_type=item&right_id=i-right"
            "&export_format=csv"
        )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/csv")
    assert 'filename="bom-compare-summarized.csv"' in (
        response.headers.get("content-disposition", "")
    )
    lines = response.text.strip().splitlines()
    assert (
        lines[0]
        == "line_key,parent_id,child_id,status,quantity_before,quantity_after,"
        "quantity_delta,uom_before,uom_after,relationship_id_before,relationship_id_after,"
        "severity,change_fields"
    )
    assert "line-add,p-1,c-1,added,,3.0,3.0,,EA,,rel-add,," in response.text


def test_compare_bom_summarized_export_markdown():
    user = SimpleNamespace(id=303, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.bom_compare_router.compare_bom",
        new=AsyncMock(return_value=_sample_compare_result()),
    ):
        response = client.get(
            "/api/v1/bom/compare/summarized/export"
            "?left_type=item&left_id=i-left"
            "&right_type=item&right_id=i-right"
            "&export_format=md"
        )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/markdown")
    assert 'filename="bom-compare-summarized.md"' in (
        response.headers.get("content-disposition", "")
    )
    assert response.text.startswith("# BOM Compare Summarized")
    assert (
        "| line_key | parent_id | child_id | status | quantity_before | quantity_after | "
        "quantity_delta | uom_before | uom_after | relationship_id_before | "
        "relationship_id_after | severity | change_fields |" in response.text
    )


def test_compare_bom_summarized_export_rejects_invalid_format():
    user = SimpleNamespace(id=304, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.bom_compare_router.compare_bom",
        new=AsyncMock(return_value=_sample_compare_result()),
    ):
        response = client.get(
            "/api/v1/bom/compare/summarized/export"
            "?left_type=item&left_id=i-left"
            "&right_type=item&right_id=i-right"
            "&export_format=xlsx"
        )

    assert response.status_code == 400
    assert response.json().get("detail") == "export_format must be json, csv or md"
