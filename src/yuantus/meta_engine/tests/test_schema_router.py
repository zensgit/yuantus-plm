import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from yuantus.api import app
from yuantus.database import get_db


# We need to simulate the dependency injection
@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def client(mock_db_session):
    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_get_schema_with_etag(client, mock_db_session):
    # Mock the Service call within the route
    with patch(
        "yuantus.meta_engine.web.schema_router.MetaSchemaService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_schema_etag.return_value = "abc12345"
        instance.get_json_schema.return_value = {"type": "object", "properties": {}}

        # 1. First request, no cache
        response = client.get("/api/meta/item-types/Part/schema")
        assert response.status_code == 200
        assert response.headers["etag"] == '"abc12345"'
        assert response.json()["type"] == "object"

        # 2. Second request, with ETag
        response_cached = client.get(
            "/api/meta/item-types/Part/schema", headers={"If-None-Match": '"abc12345"'}
        )
        assert response_cached.status_code == 304
        assert not response_cached.content  # Should be empty body


def test_get_schema_not_found(client, mock_db_session):
    with patch(
        "yuantus.meta_engine.web.schema_router.MetaSchemaService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_schema_etag.side_effect = ValueError(
            "ItemType 'Unknown' not found."
        )

        response = client.get("/api/meta/item-types/Unknown/schema")
        assert response.status_code == 404
        assert response.json()["detail"] == "ItemType 'Unknown' not found."
