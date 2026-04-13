"""
HTTP-level tests for the /ecm legacy compatibility router.
Verifies that /api/v1/ecm/... routes are accessible and return
deprecation headers.
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.models.eco import ECO, ECOState


def _client():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_user_id():
        return 1

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id_optional] = override_get_user_id
    return TestClient(app), mock_db_session


def test_ecm_impact_route_accessible_and_returns_deprecation_header():
    """GET /api/v1/ecm/items/{item_id}/impact is reachable and deprecated."""
    client, mock_db = _client()

    with patch(
        "yuantus.meta_engine.web.change_router.LegacyEcmCompatService"
    ) as compat_cls:
        compat = compat_cls.return_value
        compat.get_impact_analysis.return_value = {
            "where_used": [],
            "pending_changes": [],
        }

        resp = client.get("/api/v1/ecm/items/item-1/impact")

    assert resp.status_code == 200
    assert resp.headers.get("Deprecation") == "true"
    assert "Sunset" in resp.headers
    body = resp.json()
    assert "where_used" in body
    assert "pending_changes" in body


def test_ecm_execute_route_accessible_and_rejects_unapproved():
    """POST /api/v1/ecm/eco/{eco_id}/execute rejects non-approved ECOs."""
    client, mock_db = _client()

    with patch(
        "yuantus.meta_engine.web.change_router.LegacyEcmCompatService"
    ) as compat_cls:
        compat = compat_cls.return_value
        compat.execute_eco_compat.side_effect = ValueError(
            "Cannot execute ECO in 'draft' state. "
            "The ECO must be in 'approved' state before execution."
        )

        resp = client.post("/api/v1/ecm/eco/eco-1/execute")

    assert resp.status_code == 400
    assert "approved" in resp.json()["detail"]
