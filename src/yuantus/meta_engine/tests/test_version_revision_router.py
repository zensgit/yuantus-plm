from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.database import get_db
from yuantus.meta_engine.web.version_revision_router import version_revision_router
from yuantus.meta_engine.web.version_router import version_router


def _client_with_db():
    mock_db_session = MagicMock()

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app = FastAPI()
    app.include_router(version_revision_router, prefix="/api/v1")
    app.include_router(version_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), mock_db_session


def test_revision_scheme_endpoints_use_revision_router_service_payloads():
    client, db = _client_with_db()
    scheme = SimpleNamespace(
        id="scheme-1",
        name="Part Scheme",
        scheme_type="letter",
        initial_revision="A",
        item_type_id="part",
        is_default=True,
        description="Part revisions",
    )

    with patch("yuantus.meta_engine.web.version_revision_router.RevisionSchemeService") as svc_cls:
        svc = svc_cls.return_value
        svc.create_scheme.return_value = scheme
        svc.list_schemes.return_value = [scheme]
        svc.get_scheme_for_item_type.return_value = scheme

        create_response = client.post(
            "/api/v1/versions/schemes",
            json={
                "name": "Part Scheme",
                "scheme_type": "letter",
                "initial_revision": "A",
                "item_type_id": "part",
                "is_default": True,
                "description": "Part revisions",
            },
        )
        list_response = client.get("/api/v1/versions/schemes")
        for_type_response = client.get("/api/v1/versions/schemes/for-type/part")

    assert create_response.status_code == 200
    assert create_response.json()["id"] == "scheme-1"
    assert list_response.status_code == 200
    assert list_response.json()[0]["description"] == "Part revisions"
    assert for_type_response.status_code == 200
    assert for_type_response.json()["item_type_id"] == "part"
    svc.create_scheme.assert_called_once_with(
        name="Part Scheme",
        scheme_type="letter",
        initial_revision="A",
        item_type_id="part",
        is_default=True,
        description="Part revisions",
    )
    assert db.commit.call_count == 1


def test_revision_scheme_for_type_returns_default_when_missing():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.version_revision_router.RevisionSchemeService") as svc_cls:
        svc_cls.return_value.get_scheme_for_item_type.return_value = None
        response = client.get("/api/v1/versions/schemes/for-type/unknown")

    assert response.status_code == 200
    assert response.json() == {
        "scheme_type": "letter",
        "initial_revision": "A",
        "is_default": True,
    }


def test_revision_utility_endpoints_use_version_service():
    client, _db = _client_with_db()

    with patch("yuantus.meta_engine.web.version_revision_router.VersionService") as svc_cls:
        svc = svc_cls.return_value
        svc._next_revision.return_value = "B"
        svc.parse_revision.return_value = {"major": "A", "minor": None}
        svc.compare_revisions.return_value = -1

        next_response = client.get(
            "/api/v1/versions/revision/next",
            params={"current": "A", "scheme": "letter"},
        )
        parse_response = client.get(
            "/api/v1/versions/revision/parse",
            params={"revision": "A"},
        )
        compare_response = client.get(
            "/api/v1/versions/revision/compare",
            params={"rev_a": "A", "rev_b": "B"},
        )

    assert next_response.status_code == 200
    assert next_response.json() == {"current": "A", "next": "B", "scheme": "letter"}
    assert parse_response.status_code == 200
    assert parse_response.json()["major"] == "A"
    assert compare_response.status_code == 200
    assert compare_response.json()["description"] == "a < b"
    svc._next_revision.assert_called_once_with("A", "letter")
    svc.parse_revision.assert_called_once_with("A")
    svc.compare_revisions.assert_called_once_with("A", "B")
