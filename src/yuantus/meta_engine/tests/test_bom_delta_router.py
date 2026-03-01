from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

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


def _sample_compare_result():
    return {
        "summary": {"added": 1, "removed": 0, "changed": 1},
        "added": [
            {
                "line_key": "k-add",
                "parent_id": "p1",
                "child_id": "c1",
                "relationship_id": "r1",
                "properties": {"quantity": 2},
            }
        ],
        "removed": [],
        "changed": [
            {
                "line_key": "k-upd",
                "parent_id": "p2",
                "child_id": "c2",
                "relationship_id": "r2",
                "severity": "major",
                "changes": [
                    {
                        "field": "quantity",
                        "left": 1,
                        "right": 3,
                        "severity": "major",
                    }
                ],
            }
        ],
    }


def test_compare_bom_delta_export_supports_markdown():
    user = SimpleNamespace(id=101, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.bom_router.compare_bom",
        new=AsyncMock(return_value=_sample_compare_result()),
    ):
        response = client.get(
            "/api/v1/bom/compare/delta/export"
            "?left_type=item&left_id=i-left"
            "&right_type=item&right_id=i-right"
            "&export_format=md"
            "&fields=op&fields=line_key&fields=risk_level&fields=field&fields=before&fields=after"
        )

    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/markdown")
    assert 'filename="bom-delta-preview.md"' in (
        response.headers.get("content-disposition", "")
    )
    assert response.text.startswith("# BOM Delta Preview")
    assert "| op | line_key | risk_level | field | before | after |" in response.text


def test_compare_bom_delta_export_rejects_invalid_format():
    user = SimpleNamespace(id=101, roles=["engineer"], is_superuser=False)
    client, _db = _client_with_user(user)

    with patch(
        "yuantus.meta_engine.web.bom_router.compare_bom",
        new=AsyncMock(return_value=_sample_compare_result()),
    ):
        response = client.get(
            "/api/v1/bom/compare/delta/export"
            "?left_type=item&left_id=i-left"
            "&right_type=item&right_id=i-right"
            "&export_format=xlsx"
        )

    assert response.status_code == 400
    assert response.json().get("detail") == "export_format must be json, csv or md"
