import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile


app = FastAPI(title="Yuantus CAD Extractor", version="0.1.0")

_FILENAME_PREFIX_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
_FILENAME_REV_RE = re.compile(r"(?i)(?:rev|revision)[\s_-]*([A-Za-z0-9]+)$")
_FILENAME_VER_RE = re.compile(r"(?i)v(\d+(?:\.\d+)*)$")


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
    mode = os.getenv("CAD_EXTRACTOR_AUTH_MODE", "disabled").strip().lower()
    if mode not in {"disabled", "optional", "required"}:
        mode = "disabled"

    if mode == "disabled":
        return

    expected = os.getenv("CAD_EXTRACTOR_SERVICE_TOKEN", "").strip()
    if not expected:
        if mode == "required":
            raise HTTPException(
                status_code=401,
                detail="CAD_EXTRACTOR_SERVICE_TOKEN not configured",
            )
        return

    token = _parse_auth_token(authorization)
    if not token:
        if mode == "required":
            raise HTTPException(status_code=401, detail="Missing bearer token")
        return

    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid bearer token")


def _get_max_upload_bytes() -> int:
    raw = os.getenv("CAD_EXTRACTOR_MAX_UPLOAD_MB", "200").strip()
    try:
        mb = float(raw)
    except ValueError:
        mb = 200.0
    if mb <= 0:
        mb = 200.0
    return int(mb * 1024 * 1024)


def _get_hash_alg() -> Optional[str]:
    value = os.getenv("CAD_EXTRACTOR_HASH_ALG", "").strip()
    return value or None


async def _save_upload_to_temp(
    upload: UploadFile,
    max_bytes: int,
    hash_alg: Optional[str],
) -> Tuple[str, int, Optional[str]]:
    suffix = Path(upload.filename or "").suffix
    hasher = hashlib.new(hash_alg) if hash_alg else None
    size = 0
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(status_code=413, detail="File too large")
            tmp.write(chunk)
            if hasher:
                hasher.update(chunk)
    finally:
        tmp.close()
        await upload.close()
    digest = hasher.hexdigest() if hasher else None
    return tmp.name, size, digest


def _extract_dxf(file_path: str) -> Tuple[Dict[str, Any], Optional[str]]:
    try:
        import ezdxf  # type: ignore
    except Exception:
        return {}, "dxf_not_available"

    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        entity_count = sum(1 for _ in msp)
        layer_names = sorted({entity.dxf.layer for entity in msp if entity.dxf.layer})
        return {
            "dxf_entity_count": entity_count,
            "dxf_layer_count": len(layer_names),
            "dxf_layers": layer_names[:50],
        }, None
    except Exception as exc:
        return {}, f"dxf_parse_failed:{exc}"


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


def _extract_attributes(
    file_path: str,
    filename: Optional[str],
    cad_format: Optional[str],
    cad_connector_id: Optional[str],
    file_size: int,
    file_hash: Optional[str],
) -> Tuple[Dict[str, Any], List[str]]:
    path = Path(file_path)
    ext = path.suffix.lower().lstrip(".")
    resolved_format = cad_format or (ext.upper() if ext else None)
    stem_source = Path(filename).stem if filename else path.stem

    attrs: Dict[str, Any] = {
        "file_name": filename or path.name,
        "file_ext": ext,
        "file_size_bytes": file_size,
        "part_number": stem_source,
    }
    if resolved_format:
        attrs["cad_format"] = resolved_format
    if cad_connector_id:
        attrs["cad_connector_id"] = cad_connector_id
    if file_hash:
        attrs["file_hash"] = file_hash

    warnings: List[str] = []
    filename_attrs = _parse_filename_attributes(stem_source)
    if filename_attrs:
        attrs.update(filename_attrs)

    if ext == "dxf":
        dxf_attrs, warning = _extract_dxf(file_path)
        attrs.update(dxf_attrs)
        if warning:
            warnings.append(warning)

    return attrs, warnings


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "service": "cad-extractor"}


@app.get("/api/v1/health")
async def health_v1() -> Dict[str, Any]:
    return {"ok": True, "service": "cad-extractor"}


@app.post("/api/v1/extract")
async def extract(
    file: UploadFile = File(...),
    cad_format: Optional[str] = Form(None),
    cad_connector_id: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _check_auth(authorization)
    if not file:
        raise HTTPException(status_code=400, detail="Missing file")

    max_bytes = _get_max_upload_bytes()
    hash_alg = _get_hash_alg()
    if hash_alg and hash_alg not in hashlib.algorithms_available:
        raise HTTPException(status_code=400, detail="Unsupported hash algorithm")

    temp_path = None
    try:
        temp_path, size, digest = await _save_upload_to_temp(file, max_bytes, hash_alg)
        attrs, warnings = _extract_attributes(
            temp_path,
            file.filename,
            cad_format,
            cad_connector_id,
            size,
            digest,
        )
        return {"ok": True, "attributes": attrs, "warnings": warnings}
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
