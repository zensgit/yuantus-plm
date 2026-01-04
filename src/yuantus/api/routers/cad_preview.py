from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from yuantus.config import get_settings

router = APIRouter(prefix="/cad-preview", tags=["CAD Preview"])

_HTML_PATH = Path(__file__).resolve().parents[2] / "web" / "cad_preview.html"

_REPLACEMENTS = {
    "__CADGF_ROUTER_PUBLIC_BASE_URL__": "CADGF_ROUTER_PUBLIC_BASE_URL",
    "__CADGF_DEFAULT_EMIT__": "CADGF_DEFAULT_EMIT",
}


def _escape_js(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _load_preview_html() -> str:
    try:
        html = _HTML_PATH.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail="cad_preview.html not found") from exc
    settings = get_settings()
    for token, setting_name in _REPLACEMENTS.items():
        value = getattr(settings, setting_name, "") or ""
        if setting_name == "CADGF_ROUTER_PUBLIC_BASE_URL" and not value:
            value = getattr(settings, "CADGF_ROUTER_BASE_URL", "") or ""
        html = html.replace(token, _escape_js(str(value)))
    return html


def _router_base_url() -> str:
    settings = get_settings()
    base_url = (settings.CADGF_ROUTER_BASE_URL or "").strip()
    if not base_url:
        raise HTTPException(status_code=500, detail="CADGF router base URL not configured")
    return base_url.rstrip("/")


def _router_public_base_url() -> str:
    settings = get_settings()
    base_url = (
        settings.CADGF_ROUTER_PUBLIC_BASE_URL
        or settings.CADGF_ROUTER_BASE_URL
        or ""
    ).strip()
    return base_url.rstrip("/") if base_url else ""


def _router_headers() -> dict:
    settings = get_settings()
    token = (settings.CADGF_ROUTER_AUTH_TOKEN or "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _parse_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _rewrite_viewer_url(viewer_url: Optional[str]) -> Optional[str]:
    if not viewer_url:
        return viewer_url
    public_base = _router_public_base_url()
    if not public_base:
        return viewer_url
    parts = urlsplit(viewer_url)
    if not parts.scheme:
        return viewer_url
    query = f"?{parts.query}" if parts.query else ""
    fragment = f"#{parts.fragment}" if parts.fragment else ""
    return f"{public_base}{parts.path}{query}{fragment}"


@router.get("", response_class=HTMLResponse)
def cad_preview_page() -> HTMLResponse:
    return HTMLResponse(_load_preview_html())


@router.post("/convert")
async def cad_preview_convert(
    request: Request,
    file: UploadFile = File(...),
    emit: str = Form(""),
    project_id: str = Form(""),
    document_label: str = Form(""),
    plugin: str = Form(""),
    convert_cli: str = Form(""),
    async_flag: Optional[str] = Form(None, alias="async"),
    migrate_document: Optional[str] = Form(None),
    document_backup: Optional[str] = Form(None),
    validate_document: Optional[str] = Form(None),
    document_target: Optional[str] = Form(None),
    document_schema: str = Form(""),
) -> JSONResponse:
    base_url = _router_base_url()
    settings = get_settings()
    timeout = max(int(settings.CADGF_ROUTER_TIMEOUT_SECONDS or 60), 1)

    payload = {}
    if emit:
        payload["emit"] = emit
    if project_id:
        payload["project_id"] = project_id
    if document_label:
        payload["document_label"] = document_label
    if plugin:
        payload["plugin"] = plugin
    if convert_cli:
        payload["convert_cli"] = convert_cli
    if _parse_bool(async_flag):
        payload["async"] = "true"
    if _parse_bool(migrate_document):
        payload["migrate_document"] = "true"
    if _parse_bool(document_backup):
        payload["document_backup"] = "true"
    if _parse_bool(validate_document):
        payload["validate_document"] = "true"
    if document_target:
        target_value = document_target.strip()
        if target_value:
            try:
                target = int(target_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="invalid document_target") from exc
            payload["document_target"] = str(target)
    if document_schema:
        payload["document_schema"] = document_schema

    filename = file.filename or "upload.bin"
    content_type = file.content_type or "application/octet-stream"
    data = await file.read()
    files = {"file": (filename, data, content_type)}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}/convert",
                data=payload,
                files=files,
                headers=_router_headers(),
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"router request failed: {exc}") from exc

    try:
        result = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="router returned invalid json") from exc

    if response.status_code >= 400:
        return JSONResponse(result, status_code=response.status_code)

    task_id = result.get("task_id")
    if task_id:
        result["status_url"] = str(request.url_for("cad_preview_status", task_id=task_id))
    if "viewer_url" in result:
        result["viewer_url"] = _rewrite_viewer_url(result.get("viewer_url"))
    return JSONResponse(result, status_code=response.status_code)


@router.get("/status/{task_id}", name="cad_preview_status")
async def cad_preview_status(task_id: str, request: Request) -> JSONResponse:
    base_url = _router_base_url()
    settings = get_settings()
    timeout = max(int(settings.CADGF_ROUTER_TIMEOUT_SECONDS or 60), 1)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{base_url}/status/{task_id}",
                headers=_router_headers(),
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"router request failed: {exc}") from exc

    try:
        result = response.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="router returned invalid json") from exc

    if response.status_code < 400:
        result["status_url"] = str(request.url_for("cad_preview_status", task_id=task_id))
        if "viewer_url" in result:
            result["viewer_url"] = _rewrite_viewer_url(result.get("viewer_url"))
    return JSONResponse(result, status_code=response.status_code)
