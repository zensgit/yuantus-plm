from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
import yuantus.meta_engine.web.bom_router as bom_router_module

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db


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


def _seed_snapshot(
    *,
    snapshot_id: str,
    created_by: int,
    line_key: str,
    quantity_after: float,
    compare_mode: str = "summarized",
) -> None:
    row = {
        "snapshot_id": snapshot_id,
        "created_at": "2026-03-12T11:00:00+00:00",
        "created_by": created_by,
        "name": snapshot_id,
        "note": "seed",
        "compare": {
            "left_type": "item",
            "left_id": "left-item",
            "right_type": "item",
            "right_id": "right-item",
            "max_levels": 10,
            "effective_at": None,
            "include_child_fields": False,
            "include_relationship_props": [],
            "line_key": "child_config",
            "compare_mode": compare_mode,
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
            "quantity_delta_total": quantity_after,
        },
        "rows": [
            {
                "line_key": line_key,
                "parent_id": "p-1",
                "child_id": "c-1",
                "status": "added",
                "quantity_before": None,
                "quantity_after": quantity_after,
                "quantity_delta": quantity_after,
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


def _sample_compare_result_current():
    return {
        "summary": {
            "added": 1,
            "removed": 0,
            "changed": 0,
            "changed_major": 0,
            "changed_minor": 0,
            "changed_info": 0,
        },
        "added": [
            {
                "line_key": "line-base",
                "parent_id": "p-1",
                "child_id": "c-1",
                "relationship_id": "rel-1",
                "properties": {"quantity": 3.0, "uom": "EA"},
            }
        ],
        "removed": [],
        "changed": [],
    }


def test_compare_bom_summarized_snapshots_returns_diff_summary():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="snap-left", created_by=1, line_key="line-base", quantity_after=1.0)
    _seed_snapshot(snapshot_id="snap-right", created_by=2, line_key="line-base", quantity_after=2.0)

    user = SimpleNamespace(id=601, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/compare"
        "?left_snapshot_id=snap-left"
        "&right_snapshot_id=snap-right"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "snapshot_vs_snapshot"
    assert payload["summary"]["total_differences"] == 1
    assert payload["summary"]["changed"] == 1
    assert payload["summary"]["added"] == 0
    assert payload["summary"]["removed"] == 0
    assert payload["summary"]["left_rows"] == 1
    assert payload["summary"]["right_rows"] == 1
    assert payload["differences"][0]["change_type"] == "changed"
    assert "quantity_after" in payload["differences"][0]["changed_fields"]


def test_compare_bom_summarized_snapshots_export_csv_and_md():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="snap-left", created_by=1, line_key="line-a", quantity_after=1.0)
    _seed_snapshot(snapshot_id="snap-right", created_by=2, line_key="line-b", quantity_after=1.0)

    user = SimpleNamespace(id=602, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    csv_response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/compare/export"
        "?left_snapshot_id=snap-left"
        "&right_snapshot_id=snap-right"
        "&export_format=csv"
    )
    assert csv_response.status_code == 200
    assert csv_response.headers.get("content-type", "").startswith("text/csv")
    assert 'filename="bom-compare-summarized-snapshot-diff.csv"' in (
        csv_response.headers.get("content-disposition", "")
    )
    assert "change_type,row_key,line_key,parent_id,child_id,status" in csv_response.text

    md_response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/compare/export"
        "?left_snapshot_id=snap-left"
        "&right_snapshot_id=snap-right"
        "&export_format=md"
    )
    assert md_response.status_code == 200
    assert md_response.headers.get("content-type", "").startswith("text/markdown")
    assert md_response.text.startswith("# BOM Summarized Snapshot Diff")


def test_compare_bom_summarized_snapshot_with_current_uses_compare_bom():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="snap-current", created_by=3, line_key="line-base", quantity_after=1.0)

    user = SimpleNamespace(id=603, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)
    compare_mock = AsyncMock(return_value=_sample_compare_result_current())

    with patch("yuantus.meta_engine.web.bom_router.compare_bom", new=compare_mock):
        response = client.get(
            "/api/v1/bom/compare/summarized/snapshots/snap-current/compare/current"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "snapshot_vs_current"
    assert payload["summary"]["total_differences"] == 1
    assert payload["summary"]["changed"] == 1
    assert compare_mock.await_count == 1


def test_compare_bom_summarized_snapshot_with_current_export_json():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="snap-current", created_by=3, line_key="line-base", quantity_after=1.0)

    user = SimpleNamespace(id=604, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.bom_router.compare_bom",
        new=AsyncMock(return_value=_sample_compare_result_current()),
    ):
        response = client.get(
            "/api/v1/bom/compare/summarized/snapshots/snap-current/compare/current/export"
            "?export_format=json"
        )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert '"source": "snapshot_vs_current"' in response.text


def test_compare_bom_summarized_snapshot_diff_export_invalid_format_returns_400():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="snap-left", created_by=1, line_key="line-a", quantity_after=1.0)
    _seed_snapshot(snapshot_id="snap-right", created_by=2, line_key="line-b", quantity_after=1.0)

    user = SimpleNamespace(id=605, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/compare/export"
        "?left_snapshot_id=snap-left"
        "&right_snapshot_id=snap-right"
        "&export_format=xlsx"
    )

    assert response.status_code == 400
    assert response.json().get("detail") == "export_format must be json, csv or md"


def test_compare_bom_summarized_snapshot_missing_returns_404():
    _reset_snapshot_store()
    _seed_snapshot(snapshot_id="snap-only", created_by=1, line_key="line-a", quantity_after=1.0)

    user = SimpleNamespace(id=606, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    compare_response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/compare"
        "?left_snapshot_id=snap-only"
        "&right_snapshot_id=not-exist"
    )
    assert compare_response.status_code == 404
    assert compare_response.json().get("detail") == "snapshot not-exist not found"

    current_response = client.get(
        "/api/v1/bom/compare/summarized/snapshots/not-exist/compare/current"
    )
    assert current_response.status_code == 404
    assert current_response.json().get("detail") == "snapshot not-exist not found"
