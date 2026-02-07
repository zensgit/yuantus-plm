from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
    return TestClient(app)


def test_export_definition_denies_when_role_not_allowed():
    user = SimpleNamespace(id=2, roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    report = SimpleNamespace(
        id="rep-1",
        owner_id=1,
        is_public=True,
        allowed_roles=["admin"],
    )

    with patch("yuantus.meta_engine.web.report_router.ReportDefinitionService") as svc_cls:
        svc_cls.return_value.get_definition.return_value = report
        resp = client.post("/api/v1/reports/definitions/rep-1/export", json={})

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Permission denied"

