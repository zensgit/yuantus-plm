from fastapi import FastAPI
from fastapi.testclient import TestClient

from yuantus.api.app import create_app
from yuantus.api.middleware.auth_enforce import _is_public_path
from yuantus.api.routers.plm_workspace import router as plm_workspace_router


def test_plm_workspace_page_renders_html():
    app = FastAPI()
    app.include_router(plm_workspace_router, prefix="/api/v1")
    client = TestClient(app)

    response = client.get("/api/v1/plm-workspace")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Yuantus PLM Workspace" in response.text
    assert "Native PLM Workspace" in response.text
    assert "Object Explorer" in response.text
    assert "Approval Rail" in response.text
    assert "Open Admin Workbench" in response.text
    assert "Session Bootstrap" in response.text
    assert "Sign In" in response.text
    assert "Reuse Workbench Session" in response.text
    assert "Load Approval Rail" in response.text
    assert "Load Release Readiness" in response.text
    assert "Protected APIs" in response.text
    assert "Phase 0.5 Demo Presets" in response.text
    assert "Config Parent" in response.text
    assert "Doc UI Product" in response.text
    assert "Load BOM Demo" in response.text
    assert "Load Change Demo" in response.text
    assert "Resume Demo Sync" in response.text
    assert "Approval detail lens has not been loaded yet." in response.text
    assert "Resource detail lens has not been loaded yet." in response.text
    assert "Open Entity BOM" in response.text
    assert "Sync Active Object" in response.text
    assert "Active object context has not been loaded yet." in response.text
    assert "Change workflow has not been loaded yet." in response.text
    assert "File Attachments" in response.text
    assert "Related Documents (AML)" in response.text
    assert "Document Surface Status" in response.text
    assert "Document overview has not been loaded yet." in response.text
    assert "Document surfaces unavailable" in response.text
    assert "Current documents view is partial." in response.text
    assert "Documents partial:" in response.text
    assert "Documents unavailable" in response.text
    assert 'fetchJson("/api/aml/query"' in response.text
    assert "Attachments Source" in response.text
    assert "AML Source" in response.text
    assert "These status lines describe the two document surfaces separately: physical file attachments and AML related documents." in response.text
    assert "No AML related documents loaded yet." in response.text
    assert "Open Governance Rail" in response.text
    assert "ECO Focus" in response.text
    assert "Focus ECO" in response.text
    assert "Open Change" in response.text
    assert "Return to Source Detail" in response.text
    assert "Return to Source Change" in response.text
    assert "Source Recovery" in response.text
    assert "Source Object" in response.text
    assert "Source Files" in response.text
    assert "Source AML Docs" in response.text
    assert "Document Workspace" in response.text
    assert "Document Boundary" in response.text
    assert "Document Focus" in response.text
    assert "Document Source" in response.text
    assert "Governance Boundary" in response.text
    assert "Not published for this object" in response.text
    assert "Recent ECO Activity" in response.text
    assert "Workspace Journey" in response.text
    assert "Journey Path" in response.text
    assert "Current Object" in response.text
    assert "Handoff from" in response.text
    assert "Return to Source Product" in response.text
    assert "Return to Source Documents" in response.text
    assert "Return to Source Change" in response.text
    assert "Open Change Workspace" in response.text
    assert "Viewing related document object." in response.text
    assert "Phase 0.5 Demo Track" in response.text


def test_plm_workspace_route_registered_in_create_app():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/v1/plm-workspace" in paths


def test_plm_workspace_page_is_public_path():
    assert _is_public_path("/api/v1/plm-workspace") is True
    assert _is_public_path("/api/v1/plm-workspace/") is True
