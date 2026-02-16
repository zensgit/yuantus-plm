from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.dependencies.auth import get_current_user
from yuantus.database import get_db
from yuantus.security.auth.database import get_identity_db


def _client_with_user(user):
    mock_db_session = MagicMock()
    mock_identity_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    def override_get_identity_db():
        try:
            yield mock_identity_db_session
        finally:
            pass

    def override_get_current_user():
        return user

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_identity_db] = override_get_identity_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


def test_audit_logs_requires_admin_role():
    user = SimpleNamespace(id=2, username="viewer", roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    resp = client.get("/api/v1/esign/audit-logs")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin permission required"


def test_audit_summary_requires_admin_role():
    user = SimpleNamespace(id=2, username="viewer", roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    resp = client.get("/api/v1/esign/audit-summary")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin permission required"


def test_audit_export_requires_admin_role():
    user = SimpleNamespace(id=2, username="viewer", roles=["viewer"], is_superuser=False)
    client = _client_with_user(user)

    resp = client.get("/api/v1/esign/audit-logs/export")

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin permission required"


def test_audit_logs_allows_case_insensitive_admin_role():
    user = SimpleNamespace(id=2, username="admin", roles=[" Admin "], is_superuser=False)
    client = _client_with_user(user)

    svc = MagicMock()
    svc.list_audit_logs.return_value = []
    with patch("yuantus.meta_engine.web.esign_router._service", return_value=svc):
        resp = client.get("/api/v1/esign/audit-logs")

    assert resp.status_code == 200
    assert resp.json() == {"items": []}
    svc.list_audit_logs.assert_called_once()


def test_audit_summary_allows_superuser_without_admin_role():
    user = SimpleNamespace(id=2, username="root", roles=["viewer"], is_superuser=True)
    client = _client_with_user(user)

    svc = MagicMock()
    svc.get_audit_summary.return_value = {"total": 0, "by_action": {}}
    with patch("yuantus.meta_engine.web.esign_router._service", return_value=svc):
        resp = client.get("/api/v1/esign/audit-summary")

    assert resp.status_code == 200
    assert resp.json() == {"total": 0, "by_action": {}}
    svc.get_audit_summary.assert_called_once()
