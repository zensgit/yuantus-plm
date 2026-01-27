import base64
import hashlib
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response


app = FastAPI(title="Yuantus CAD Connector Stub", version="0.1.0")

_FILENAME_PREFIX_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
_FILENAME_REV_RE = re.compile(r"(?i)(?:rev|revision)[\s_-]*([A-Za-z0-9]+)$")
_FILENAME_VER_RE = re.compile(r"(?i)v(\d+(?:\.\d+)*)$")

ARTIFACTS: Dict[str, Dict[str, Any]] = {}
JOBS: Dict[str, Dict[str, Any]] = {}

GLTF_JSON = {
    "asset": {"version": "2.0", "generator": "yuantus-cad-connector-stub"},
    "scenes": [{"nodes": [0]}],
    "nodes": [{"mesh": 0}],
    "meshes": [{"primitives": [{"attributes": {}}]}],
}
GLTF_BYTES = ("{\n" + "\n".join(["  \"asset\": {\"version\": \"2.0\"}", "}"]) + "\n").encode(
    "utf-8"
)
MESH_BIN_BYTES = b"\x00\x00\x00\x00"
PREVIEW_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
)


def _build_bom_payload(file_name: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
    name = (file_name or "").lower()
    is_assembly = any(
        token in name
        for token in (
            ".sldasm",
            ".asm",
            ".iam",
            ".catproduct",
            "assembly",
        )
    )
    if not is_assembly:
        return {"nodes": [], "edges": []}

    root_id = "root"
    part_number = attributes.get("part_number") or Path(file_name).stem
    child_part = f"{part_number}-01"
    nodes = [
        {"id": root_id, "part_number": part_number, "name": attributes.get("description")},
        {"id": "child-1", "part_number": child_part, "name": "Generated Child"},
    ]
    edges = [
        {
            "parent": root_id,
            "child": "child-1",
            "quantity": 2,
            "uom": "EA",
            "find_num": "10",
        }
    ]
    return {"root": root_id, "nodes": nodes, "edges": edges}


def _parse_auth_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1].strip()
        return token or None
    token = authorization.strip()
    return token or None


def _check_auth(authorization: Optional[str]) -> None:
    mode = os.getenv("CAD_CONNECTOR_AUTH_MODE", "disabled").strip().lower()
    if mode not in {"disabled", "optional", "required"}:
        mode = "disabled"

    if mode == "disabled":
        return

    expected = os.getenv("CAD_CONNECTOR_SERVICE_TOKEN", "").strip()
    if not expected:
        if mode == "required":
            raise HTTPException(status_code=401, detail="CAD_CONNECTOR_SERVICE_TOKEN not configured")
        return

    token = _parse_auth_token(authorization)
    if not token:
        if mode == "required":
            raise HTTPException(status_code=401, detail="Missing bearer token")
        return

    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid bearer token")


def _parse_filename_attributes(stem: str) -> Dict[str, Any]:
    stem = stem.strip()
    if not stem:
        return {}

    attrs: Dict[str, Any] = {}
    revision = None

    match = _FILENAME_REV_RE.search(stem)
    if match:
        revision = match.group(1)
        stem = stem[: match.start()].rstrip(" _-")
    else:
        match = _FILENAME_VER_RE.search(stem)
        if match:
            revision = f"v{match.group(1)}"
            stem = stem[: match.start()].rstrip(" _-")

    if revision:
        attrs["revision"] = revision

    match = _FILENAME_PREFIX_RE.match(stem)
    if match:
        part_number = match.group(1)
        remainder = stem[len(part_number) :].lstrip(" _-")
        if part_number:
            attrs["part_number"] = part_number
        if remainder:
            attrs["description"] = remainder
        return attrs

    attrs["description"] = stem
    return attrs


def _build_artifacts(base_url: str, artifact_id: str, mode: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
    modes = {m.strip().lower() for m in mode.split(",") if m.strip()}
    if not modes:
        modes = {"all"}
    wants_all = "all" in modes or "*" in modes

    include_extract = wants_all or "extract" in modes
    include_geometry = wants_all or "geometry" in modes
    include_preview = wants_all or "preview" in modes
    include_bom = wants_all or "bom" in modes

    artifacts: Dict[str, Any] = {}
    if include_geometry:
        artifacts["geometry"] = {
            "gltf_url": f"{base_url}/artifacts/{artifact_id}/mesh.gltf",
            "bin_url": f"{base_url}/artifacts/{artifact_id}/mesh.bin",
            "bbox": [0, 0, 0, 1, 1, 1],
        }
    if include_preview:
        artifacts["preview"] = {"png_url": f"{base_url}/artifacts/{artifact_id}/preview.png"}
    if include_extract:
        artifacts["attributes"] = attributes
    if include_bom:
        artifacts["bom"] = _build_bom_payload(attributes.get("file_name") or "", attributes)
    return artifacts


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "service": "cad-connector"}


@app.get("/api/v1/health")
async def health_v1() -> Dict[str, Any]:
    return {"ok": True, "service": "cad-connector"}


@app.get("/capabilities")
async def capabilities() -> Dict[str, Any]:
    return {
        "formats": ["dwg", "dxf", "step", "stp", "prt", "sldprt", "catpart"],
        "features": {"extract": True, "geometry": True, "preview": True, "bom": True},
        "limits": {"max_bytes": 10 * 1024 * 1024 * 1024},
    }


@app.post("/convert")
@app.post("/api/v1/convert")
async def convert(
    request: Request,
    file: Optional[UploadFile] = File(None),
    file_url: Optional[str] = Form(None),
    format: Optional[str] = Form(None),
    mode: str = Form("all"),
    async_mode: bool = Form(False),
    tenant_id: Optional[str] = Form(None),
    org_id: Optional[str] = Form(None),
    callback_url: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_auth(authorization)

    if file is None and not file_url:
        raise HTTPException(status_code=400, detail="Missing file or file_url")

    file_name = None
    content = b""
    if file is not None:
        file_name = file.filename
        content = await file.read()
        await file.close()
    elif file_url:
        file_name = Path(file_url).name

    if not file_name:
        raise HTTPException(status_code=400, detail="Missing file name")

    ext = Path(file_name).suffix.lower().lstrip(".")
    resolved_format = format or (ext.upper() if ext else "")
    stem = Path(file_name).stem
    attrs = {
        "file_name": file_name,
        "file_ext": ext,
        "file_size_bytes": len(content),
        "cad_format": resolved_format,
        "tenant_id": tenant_id,
        "org_id": org_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    attrs.update(_parse_filename_attributes(stem))

    hash_alg = os.getenv("CAD_CONNECTOR_HASH_ALG", "").strip().lower()
    if hash_alg:
        try:
            digest = hashlib.new(hash_alg, content).hexdigest()
            attrs["file_hash"] = digest
        except Exception:
            attrs["file_hash"] = None

    artifact_id = uuid.uuid4().hex
    base_url = str(request.base_url).rstrip("/")
    artifacts = _build_artifacts(base_url, artifact_id, mode, attrs)

    ARTIFACTS[artifact_id] = {
        "artifacts": artifacts,
        "attributes": attrs,
    }

    job_id = None
    if async_mode:
        job_id = uuid.uuid4().hex
        JOBS[job_id] = {"status": "completed", "artifacts": artifacts}

    return {
        "ok": True,
        "job_id": job_id,
        "callback_url": callback_url,
        "artifacts": artifacts,
    }


@app.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "job_id": job_id, **job}


@app.get("/artifacts/{artifact_id}/mesh.gltf")
async def artifact_gltf(artifact_id: str) -> Response:
    if artifact_id not in ARTIFACTS:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return Response(content=GLTF_BYTES, media_type="model/gltf+json")


@app.get("/artifacts/{artifact_id}/mesh.bin")
async def artifact_bin(artifact_id: str) -> Response:
    if artifact_id not in ARTIFACTS:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return Response(content=MESH_BIN_BYTES, media_type="application/octet-stream")


@app.get("/artifacts/{artifact_id}/preview.png")
async def artifact_preview(artifact_id: str) -> Response:
    if artifact_id not in ARTIFACTS:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return Response(content=PREVIEW_PNG_BYTES, media_type="image/png")
