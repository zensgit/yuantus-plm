"""Direct route behavior tests for spare_router (G5 spare-parts, OdooPLM parity).

Fully mocked (MagicMock db session + patched MetaPermissionService / SpareService);
runs DB-off, mirroring ``test_bom_substitutes_router.py``. Covers the 4 endpoints:
  - GET    /api/v1/items/{item_id}/spares
  - POST   /api/v1/items/{item_id}/spares
  - DELETE /api/v1/items/{item_id}/spares/{spare_id}
  - GET    /api/v1/items/{item_id}/spares/explode
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.web.spare_router import spare_router


_PERM = "yuantus.meta_engine.web.spare_router.MetaPermissionService"
_SVC = "yuantus.meta_engine.web.spare_router.SpareService"


def _current_user() -> CurrentUser:
    return CurrentUser(
        id=1,
        tenant_id="tenant-1",
        org_id="org-1",
        username="admin",
        email="admin@example.com",
        roles=["admin"],
        is_superuser=True,
    )


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

    app = FastAPI()
    app.include_router(spare_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _current_user
    return TestClient(app)


def _part(item_id="PART-1", item_type_id="Part", source_id=None):
    return SimpleNamespace(
        id=item_id,
        item_type_id=item_type_id,
        source_id=source_id,
        state="Active",
    )


# --------------------------------------------------------------------------
# GET /spares (list)
# --------------------------------------------------------------------------


def test_list_spares_item_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.get("/api/v1/items/PART-1/spares")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item PART-1 not found"


def test_list_spares_invalid_type_returns_400(client, mock_db_session):
    mock_db_session.get.return_value = _part(item_type_id="Document")
    response = client.get("/api/v1/items/PART-1/spares")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Part type"


def test_list_spares_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.return_value = _part()
    with patch(_PERM) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.get("/api/v1/items/PART-1/spares")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_list_spares_success_returns_count_and_entries(client, mock_db_session):
    mock_db_session.get.return_value = _part()
    with patch(_PERM) as mock_perm, patch(_SVC) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.list_spares.return_value = [
            {
                "id": "SPARE-REL-1",
                "spare_item_id": "SPARE-1",
                "spare_part": {"id": "SPARE-1"},
                "relationship": {"id": "SPARE-REL-1"},
            }
        ]
        response = client.get("/api/v1/items/PART-1/spares")

    assert response.status_code == 200
    body = response.json()
    assert body["item_id"] == "PART-1"
    assert body["count"] == 1
    assert body["spares"][0]["id"] == "SPARE-REL-1"
    mock_service.return_value.list_spares.assert_called_once_with("PART-1")


# --------------------------------------------------------------------------
# POST /spares (add)
# --------------------------------------------------------------------------


def test_add_spare_self_reference_returns_400(client, mock_db_session):
    response = client.post(
        "/api/v1/items/PART-1/spares", json={"spare_item_id": "PART-1"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Item cannot be a spare of itself"


def test_add_spare_item_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.post(
        "/api/v1/items/PART-1/spares", json={"spare_item_id": "SPARE-1"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Item PART-1 not found"


def test_add_spare_spare_item_not_found_returns_404(client, mock_db_session):
    def get_side_effect(_model, item_id):
        return {"PART-1": _part("PART-1")}.get(item_id)

    mock_db_session.get.side_effect = get_side_effect
    response = client.post(
        "/api/v1/items/PART-1/spares", json={"spare_item_id": "SPARE-1"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Item SPARE-1 not found"


def test_add_spare_invalid_part_type_returns_400(client, mock_db_session):
    mock_db_session.get.return_value = _part(item_type_id="Document")
    response = client.post(
        "/api/v1/items/PART-1/spares", json={"spare_item_id": "SPARE-1"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Part type"


def test_add_spare_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.side_effect = lambda _m, i: _part(i)
    with patch(_PERM) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.post(
            "/api/v1/items/PART-1/spares", json={"spare_item_id": "SPARE-1"}
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_add_spare_value_error_mapping(client, mock_db_session):
    mock_db_session.get.side_effect = lambda _m, i: _part(i)
    cases = [
        ("Invalid Part ID: SPARE-1", 404),
        ("Spare relationship already exists", 400),
    ]
    for message, expected_status in cases:
        with patch(_PERM) as mock_perm, patch(_SVC) as mock_service:
            mock_perm.return_value.check_permission.return_value = True
            mock_service.return_value.add_spare.side_effect = ValueError(message)
            response = client.post(
                "/api/v1/items/PART-1/spares", json={"spare_item_id": "SPARE-1"}
            )
        assert response.status_code == expected_status
        assert response.json()["detail"] == message


def test_add_spare_success_returns_relationship_id(client, mock_db_session):
    mock_db_session.get.side_effect = lambda _m, i: _part(i)
    with patch(_PERM) as mock_perm, patch(_SVC) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.add_spare.return_value = SimpleNamespace(
            id="SPARE-REL-1"
        )
        response = client.post(
            "/api/v1/items/PART-1/spares",
            json={"spare_item_id": "SPARE-1", "properties": {"quantity": 2}},
        )
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "spare_id": "SPARE-REL-1",
        "item_id": "PART-1",
        "spare_item_id": "SPARE-1",
        "properties": {"quantity": 2},
    }
    mock_service.return_value.add_spare.assert_called_once_with(
        item_id="PART-1",
        spare_item_id="SPARE-1",
        properties={"quantity": 2},
        user_id=1,
    )


# --------------------------------------------------------------------------
# DELETE /spares/{spare_id} (remove)
# --------------------------------------------------------------------------


def test_remove_spare_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.delete("/api/v1/items/PART-1/spares/SPARE-REL-1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Spare relationship not found"


def test_remove_spare_wrong_type_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = _part(item_type_id="Part Equivalent")
    response = client.delete("/api/v1/items/PART-1/spares/SPARE-REL-1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Spare relationship not found"


def test_remove_spare_wrong_owner_returns_404(client, mock_db_session):
    rel = SimpleNamespace(
        id="SPARE-REL-1", item_type_id="Part Spare", source_id="OTHER-PART"
    )
    mock_db_session.get.return_value = rel
    response = client.delete("/api/v1/items/PART-1/spares/SPARE-REL-1")
    assert response.status_code == 404
    assert response.json()["detail"] == "Spare relationship not found"


def test_remove_spare_permission_denied_returns_403(client, mock_db_session):
    rel = SimpleNamespace(
        id="SPARE-REL-1", item_type_id="Part Spare", source_id="PART-1"
    )
    mock_db_session.get.return_value = rel
    with patch(_PERM) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.delete("/api/v1/items/PART-1/spares/SPARE-REL-1")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_remove_spare_value_error_maps_to_404(client, mock_db_session):
    rel = SimpleNamespace(
        id="SPARE-REL-1", item_type_id="Part Spare", source_id="PART-1"
    )
    mock_db_session.get.return_value = rel
    with patch(_PERM) as mock_perm, patch(_SVC) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.remove_spare.side_effect = ValueError("missing")
        response = client.delete("/api/v1/items/PART-1/spares/SPARE-REL-1")
    assert response.status_code == 404
    assert response.json()["detail"] == "missing"


def test_remove_spare_success_returns_removed_id(client, mock_db_session):
    rel = SimpleNamespace(
        id="SPARE-REL-1", item_type_id="Part Spare", source_id="PART-1"
    )
    mock_db_session.get.return_value = rel
    with patch(_PERM) as mock_perm, patch(_SVC) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        response = client.delete("/api/v1/items/PART-1/spares/SPARE-REL-1")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "spare_id": "SPARE-REL-1"}
    mock_service.return_value.remove_spare.assert_called_once_with(
        "SPARE-REL-1", user_id=1
    )


# --------------------------------------------------------------------------
# GET /spares/explode
# --------------------------------------------------------------------------


def test_explode_item_not_found_returns_404(client, mock_db_session):
    mock_db_session.get.return_value = None
    response = client.get("/api/v1/items/PART-1/spares/explode")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item PART-1 not found"


def test_explode_invalid_type_returns_400(client, mock_db_session):
    mock_db_session.get.return_value = _part(item_type_id="Document")
    response = client.get("/api/v1/items/PART-1/spares/explode")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Part type"


def test_explode_permission_denied_returns_403(client, mock_db_session):
    mock_db_session.get.return_value = _part()
    with patch(_PERM) as mock_perm:
        mock_perm.return_value.check_permission.return_value = False
        response = client.get("/api/v1/items/PART-1/spares/explode")
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_explode_success_aggregates_count_and_passes_levels(client, mock_db_session):
    mock_db_session.get.return_value = _part()
    groups = [
        {
            "item_id": "PART-1",
            "count": 2,
            "spares": [
                {
                    "id": "R1",
                    "spare_item_id": "S1",
                    "spare_part": None,
                    "relationship": {"id": "R1"},
                },
                {
                    "id": "R2",
                    "spare_item_id": "S2",
                    "spare_part": None,
                    "relationship": {"id": "R2"},
                },
            ],
        },
        {
            "item_id": "CHILD-1",
            "count": 1,
            "spares": [
                {
                    "id": "R3",
                    "spare_item_id": "S3",
                    "spare_part": None,
                    "relationship": {"id": "R3"},
                }
            ],
        },
    ]
    with patch(_PERM) as mock_perm, patch(_SVC) as mock_service:
        mock_perm.return_value.check_permission.return_value = True
        mock_service.return_value.explode_spares.return_value = groups
        response = client.get("/api/v1/items/PART-1/spares/explode?levels=5")

    assert response.status_code == 200
    body = response.json()
    assert body["item_id"] == "PART-1"
    assert body["levels"] == 5
    assert body["count"] == 3  # 2 + 1 aggregated across groups
    assert len(body["groups"]) == 2
    mock_service.return_value.explode_spares.assert_called_once_with("PART-1", levels=5)
