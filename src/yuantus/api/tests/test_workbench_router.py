from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.middleware.auth_enforce import _is_public_path
from yuantus.api.routers.workbench import router as workbench_router


def test_workbench_page_renders_html():
    app = FastAPI()
    app.include_router(workbench_router, prefix="/api/v1")
    client = TestClient(app)

    response = client.get("/api/v1/workbench")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Yuantus PLM Workbench" in response.text
    assert "ECO Operations" in response.text
    assert "PLM Workbench" in response.text
    assert "Workflow Handoff" in response.text
    assert "Structure and Sync Lens" in response.text
    assert "Approval Inbox" in response.text
    assert "Release Orchestration" in response.text
    assert "Object Drilldown" in response.text
    assert "CAD Material Profiles" in response.text
    assert "Structured Rule Builder" in response.text
    assert "CAD Write Confirmation" in response.text
    assert 'id="cad-material-field-name"' in response.text
    assert 'id="cad-material-compose-template"' in response.text
    assert 'id="cad-material-match-fields"' in response.text
    assert 'id="cad-material-write-fields"' in response.text
    assert 'data-action="cad-material-list-profiles"' in response.text
    assert 'data-action="cad-material-preview-config"' in response.text
    assert 'data-action="cad-material-diff-preview"' in response.text
    assert 'data-action="cad-material-export-config"' in response.text


def test_workbench_cad_material_actions_are_wired():
    app = FastAPI()
    app.include_router(workbench_router, prefix="/api/v1")
    client = TestClient(app)

    response = client.get("/api/v1/workbench")

    assert response.status_code == 200
    for action in [
        "cad-material-upsert-field",
        "cad-material-set-compose",
        "cad-material-set-matching",
        "cad-material-confirm-diff",
        "cad-material-list-profiles",
        "cad-material-get-config",
        "cad-material-preview-config",
        "cad-material-save-config",
        "cad-material-delete-config",
        "cad-material-compose",
        "cad-material-diff-preview",
        "cad-material-outbound",
        "cad-material-export-config",
        "cad-material-import-dry",
        "cad-material-import-config",
    ]:
        assert f'data-action="{action}"' in response.text
        assert f'case "{action}"' in response.text


def test_workbench_route_registered_in_create_app():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/v1/workbench" in paths
    assert "/favicon.ico" in paths


def test_favicon_returns_no_content():
    app = create_app()
    client = TestClient(app)

    response = client.get("/favicon.ico")

    assert response.status_code == 204


def test_workbench_page_is_public_path():
    assert _is_public_path("/favicon.ico") is True
    assert _is_public_path("/api/v1/workbench") is True
    assert _is_public_path("/api/v1/workbench/") is True
