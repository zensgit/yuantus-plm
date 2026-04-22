from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
import yuantus.meta_engine.web.bom_compare_router as bom_router_module

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


def _reset_snapshot_store() -> None:
    with bom_router_module._BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        bom_router_module._BOM_COMPARE_SUMMARIZED_SNAPSHOTS.clear()


def _sample_compare_result():
    return {
        "summary": {
            "added": 1,
            "removed": 0,
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
                "properties": {"quantity": 2, "uom": "EA"},
            }
        ],
        "removed": [],
        "changed": [
            {
                "line_key": "line-change",
                "parent_id": "p-2",
                "child_id": "c-2",
                "relationship_id": "rel-change",
                "severity": "major",
                "before": {"quantity": 1, "uom": "EA"},
                "after": {"quantity": 3, "uom": "EA"},
                "changes": [{"field": "quantity", "left": 1, "right": 3, "severity": "major"}],
            }
        ],
    }


def _seed_snapshot(*, snapshot_id: str, created_by: int, name: str) -> None:
    row = {
        "snapshot_id": snapshot_id,
        "created_at": "2026-03-12T10:00:00+00:00",
        "created_by": created_by,
        "name": name,
        "note": "seed",
        "compare": {
            "left_type": "item",
            "left_id": "left",
            "right_type": "item",
            "right_id": "right",
            "max_levels": 10,
            "effective_at": None,
            "include_child_fields": False,
            "include_relationship_props": [],
            "line_key": "child_config",
            "compare_mode": "summarized",
            "include_substitutes": False,
            "include_effectivity": False,
        },
        "summary": {
            "total_rows": 1,
            "total": 1,
            "added": 1,
            "removed": 0,
            "changed": 0,
            "changed_major": 0,
            "changed_minor": 0,
            "changed_info": 0,
            "quantity_delta_total": 1.0,
        },
        "rows": [
            {
                "line_key": "row-1",
                "parent_id": "p-1",
                "child_id": "c-1",
                "status": "added",
                "quantity_before": None,
                "quantity_after": 1.0,
                "quantity_delta": 1.0,
                "uom_before": None,
                "uom_after": "EA",
                "relationship_id_before": None,
                "relationship_id_after": "rel-1",
                "severity": None,
                "change_fields": [],
            }
        ],
        "row_total": 1,
    }
    with bom_router_module._BOM_COMPARE_SUMMARIZED_SNAPSHOTS_LOCK:
        bom_router_module._BOM_COMPARE_SUMMARIZED_SNAPSHOTS.append(row)


def test_create_bom_summarized_snapshot_saves_record():
    _reset_snapshot_store()
    user = SimpleNamespace(id=501, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)
    compare_mock = AsyncMock(return_value=_sample_compare_result())

    with patch("yuantus.meta_engine.web.bom_compare_router.compare_bom", new=compare_mock):
        response = client.post(
            "/api/v1/bom/compare/summarized/snapshots",
            json={
                "left_type": "item",
                "left_id": "left-item",
                "right_type": "item",
                "right_id": "right-item",
                "name": "Baseline A",
                "note": "first",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"].startswith("bom-compare-summarized-snapshot-")
    assert payload["created_by"] == 501
    assert payload["name"] == "Baseline A"
    assert payload["summary"]["added"] == 1
    assert len(payload["rows"]) == 2
    assert payload["compare"]["compare_mode"] == "summarized"
    assert compare_mock.await_args.kwargs["compare_mode"] == "summarized"


def test_list_bom_summarized_snapshots_supports_paging_and_filters():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="s-1", created_by=1, name="Alpha baseline")
    _seed_snapshot(snapshot_id="s-2", created_by=2, name="Beta baseline")
    user = SimpleNamespace(id=900, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.get(
        "/api/v1/bom/compare/summarized/snapshots"
        "?created_by=1"
        "&name_contains=alpha"
        "&limit=5"
        "&offset=0"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["count"] == 1
    assert payload["limit"] == 5
    assert payload["offset"] == 0
    assert len(payload["snapshots"]) == 1
    assert payload["snapshots"][0]["snapshot_id"] == "s-1"
    assert payload["snapshots"][0]["row_count"] == 1
    assert payload["snapshots"][0]["rows"] is None


def test_get_bom_summarized_snapshot_detail_returns_record():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="s-detail", created_by=3, name="Detail baseline")
    user = SimpleNamespace(id=901, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.get("/api/v1/bom/compare/summarized/snapshots/s-detail")

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot_id"] == "s-detail"
    assert payload["created_by"] == 3
    assert payload["summary"]["total_rows"] == 1
    assert len(payload["rows"]) == 1


def test_export_bom_summarized_snapshot_supports_csv_and_markdown():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="s-export", created_by=4, name="Export baseline")
    user = SimpleNamespace(id=902, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    csv_response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/s-export/export?export_format=csv"
    )
    assert csv_response.status_code == 200
    assert csv_response.headers.get("content-type", "").startswith("text/csv")
    assert 'filename="bom-compare-summarized-snapshot-s-export.csv"' in (
        csv_response.headers.get("content-disposition", "")
    )
    assert (
        "line_key,parent_id,child_id,status,quantity_before,quantity_after,quantity_delta"
        in csv_response.text
    )

    md_response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/s-export/export?export_format=md"
    )
    assert md_response.status_code == 200
    assert md_response.headers.get("content-type", "").startswith("text/markdown")
    assert md_response.text.startswith("# BOM Compare Summarized")


def test_export_bom_summarized_snapshot_invalid_format_returns_400():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="s-invalid-format", created_by=5, name="Invalid format")
    user = SimpleNamespace(id=903, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/s-invalid-format/export?export_format=xlsx"
    )
    assert response.status_code == 400
    assert response.json().get("detail") == "export_format must be json, csv or md"


def test_bom_summarized_snapshot_missing_returns_404():
    _reset_snapshot_store()
    user = SimpleNamespace(id=904, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    detail_response = client.get("/api/v1/bom/compare/summarized/snapshots/not-exist")
    assert detail_response.status_code == 404
    assert detail_response.json().get("detail") == "snapshot not-exist not found"

    export_response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/not-exist/export?export_format=csv"
    )
    assert export_response.status_code == 404
    assert export_response.json().get("detail") == "snapshot not-exist not found"
