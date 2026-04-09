from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from yuantus.config import get_settings

router = APIRouter(prefix="/plm-workspace", tags=["PLM Workspace"])

_HTML_PATH = Path(__file__).resolve().parents[2] / "web" / "plm_workspace.html"

_API_BASE = "/api/v1"
_SETTING_REPLACEMENTS = {
    "__YUANTUS_TENANT_HEADER__": "TENANT_HEADER",
    "__YUANTUS_ORG_HEADER__": "ORG_HEADER",
    "__YUANTUS_AUTH_MODE__": "AUTH_MODE",
}


def _escape_js(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _load_workspace_html() -> str:
    try:
        html = _HTML_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500, detail="plm_workspace.html not found"
        ) from exc

    html = html.replace("__YUANTUS_API_BASE__", _escape_js(_API_BASE))
    settings = get_settings()
    for token, setting_name in _SETTING_REPLACEMENTS.items():
        value = getattr(settings, setting_name, "")
        html = html.replace(token, _escape_js(str(value or "")))
    return html


@router.get("", response_class=HTMLResponse)
def plm_workspace_page() -> HTMLResponse:
    return HTMLResponse(_load_workspace_html())
