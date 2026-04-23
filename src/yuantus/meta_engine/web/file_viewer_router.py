"""
File viewer/readiness router.

This module owns the read-only viewer, geometry, and CAD artifact endpoints
split out of the legacy file router.
"""

from __future__ import annotations

from datetime import datetime
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.cad_converter_service import CADConverterService
from yuantus.meta_engine.services.file_service import FileService
from yuantus.security.auth.database import get_identity_db_session
from yuantus.security.rbac.models import RBACUser


file_viewer_router = APIRouter(prefix="/file", tags=["File Management"])

VAULT_DIR = get_settings().LOCAL_STORAGE_PATH

C11_MAX_BATCH_FILE_IDS = 200
C11_DEFAULT_AUDIT_HISTORY_LIMIT = 3


class C11BatchRequest(BaseModel):
    """Request payload for C11 batch endpoints."""

    file_ids: List[str]


def _guess_media_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    media_types = {
        ".obj": "model/obj",
        ".gltf": "model/gltf+json",
        ".glb": "model/gltf-binary",
        ".stl": "model/stl",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".json": "application/json",
        ".bin": "application/octet-stream",
    }
    return media_types.get(ext, "application/octet-stream")


def _serve_storage_path(storage_path: str, media_type: str, error_prefix: str):
    file_service = FileService()

    # Try local path first (for local storage or performance)
    local_path = file_service.get_local_path(storage_path)
    if local_path and os.path.exists(local_path):
        return FileResponse(path=local_path, media_type=media_type)

    # Try presigned URL (S3) - return 302 redirect
    try:
        url = file_service.get_presigned_url(storage_path)
        return RedirectResponse(url=url, status_code=302)
    except NotImplementedError:
        pass

    # Fallback: stream from storage
    try:
        output_stream = io.BytesIO()
        file_service.download_file(storage_path, output_stream)
        output_stream.seek(0)
        return StreamingResponse(
            output_stream,
            media_type=media_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"{error_prefix} download failed: {str(e)}"
        )


def _sanitize_asset_name(asset_name: str) -> str:
    safe_name = Path(asset_name).name
    if not safe_name or safe_name != asset_name:
        raise HTTPException(status_code=400, detail="Invalid asset name")
    return safe_name


def _load_manifest_payload(file_container: FileContainer) -> dict:
    file_service = FileService()
    output_stream = io.BytesIO()
    try:
        file_service.download_file(file_container.cad_manifest_path, output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"CAD manifest download failed: {exc}"
        ) from exc
    output_stream.seek(0)
    try:
        return json.load(output_stream)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail="CAD manifest invalid JSON"
        ) from exc


def _rewrite_cad_manifest_urls(
    request: Request, file_container: FileContainer, manifest: dict
) -> dict:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return manifest
    if file_container.cad_document_path:
        artifacts["document_json"] = str(
            request.url_for("get_cad_document", file_id=file_container.id)
        )
    if file_container.cad_metadata_path:
        artifacts["mesh_metadata"] = str(
            request.url_for("get_cad_metadata", file_id=file_container.id)
        )
    gltf_name = artifacts.get("mesh_gltf") or (
        Path(file_container.geometry_path).name if file_container.geometry_path else ""
    )
    if gltf_name:
        safe_name = _sanitize_asset_name(Path(gltf_name).name)
        artifacts["mesh_gltf"] = str(
            request.url_for(
                "get_cad_asset",
                file_id=file_container.id,
                asset_name=safe_name,
            )
        )
    manifest["artifacts"] = artifacts
    return manifest


def _normalize_batch_file_ids(
    file_ids: Any, *, max_count: int = C11_MAX_BATCH_FILE_IDS
) -> List[str]:
    """Normalize and validate a batch of file ids."""
    if not isinstance(file_ids, list):
        raise HTTPException(status_code=400, detail="file_ids list required")
    normalized: List[str] = []
    for raw in file_ids:
        if not isinstance(raw, str):
            raise HTTPException(status_code=400, detail="file_ids must be strings")
        value = raw.strip()
        if not value:
            raise HTTPException(status_code=400, detail="file_ids contains empty value")
        normalized.append(value)
    if not normalized:
        raise HTTPException(status_code=400, detail="file_ids list required")
    if len(normalized) > max_count:
        raise HTTPException(
            status_code=400,
            detail=f"file_ids exceeds max count: {max_count}",
        )
    return normalized


def _resolve_reviewer_identity(
    reviewer_id: Optional[int],
    include_profile: bool = False,
) -> Optional[Dict[str, Optional[Union[int, str]]]]:
    if reviewer_id is None:
        return None
    if not include_profile:
        return {"id": reviewer_id}

    try:
        with get_identity_db_session() as identity_db:
            user = identity_db.query(RBACUser).filter(RBACUser.id == reviewer_id).first()
            if not user:
                return {"id": reviewer_id}
            return {
                "id": user.id,
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
            }
    except Exception:
        return {"id": reviewer_id}


def _load_file_change_log_history(
    db: Session, file_id: str, limit: int
) -> List[Dict[str, Optional[Union[str, int, Dict[str, Any]]]]]:
    if limit <= 0:
        return []

    try:
        rows = (
            db.query(CadChangeLog)
            .filter(CadChangeLog.file_id == file_id)
            .order_by(CadChangeLog.created_at.desc())
            .limit(limit)
            .all()
        )
        rows_list = list(rows) if rows is not None else []
    except Exception:
        return []

    return [
        {
            "id": row.id,
            "action": row.action,
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
            "user_id": getattr(row, "user_id", None),
            "payload": getattr(row, "payload", None) or {},
        }
        for row in rows_list
        if getattr(row, "id", None)
    ]


def _build_c11_consumer_proof(
    file_container: FileContainer,
    *,
    db: Session,
    history_limit: int = 0,
    include_audit: bool = False,
    include_reviewer_profile: bool = False,
) -> Dict[str, Any]:
    reviewed_at = file_container.cad_reviewed_at
    proof: Dict[str, Any] = {
        "review": {
            "state": file_container.cad_review_state,
            "note": file_container.cad_review_note,
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "reviewed_by": _resolve_reviewer_identity(
                file_container.cad_review_by_id,
                include_profile=include_reviewer_profile,
            ),
        },
        "review_api": f"/api/v1/cad/files/{file_container.id}/review",
        "history_api": f"/api/v1/cad/files/{file_container.id}/history",
    }

    if not include_audit:
        proof["audit"] = {
            "enabled": False,
            "history_count": None,
            "latest": None,
        }
        return proof

    history = _load_file_change_log_history(db, file_container.id, history_limit)
    proof["audit"] = {
        "enabled": True,
        "history_count": len(history),
        "latest": history[0] if history else None,
        "history": history,
    }
    return proof


def _build_c11_export_row(
    file_container: Optional[FileContainer],
    *,
    file_id: str,
    history_limit: int,
    include_audit: bool,
    include_reviewer_profile: bool,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    if not file_container:
        return {
            "file_id": file_id,
            "found": False,
            "filename": None,
            "viewer_mode": "not_found",
            "is_viewer_ready": False,
            "geometry_format": None,
            "asset_count": 0,
            "available_assets": [],
            "blocking_reasons": ["file_not_found"],
            "proof": None,
        }

    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    readiness = converter.assess_viewer_readiness(file_container)
    proof = _build_c11_consumer_proof(
        file_container,
        db=db,
        include_audit=include_audit,
        include_reviewer_profile=include_reviewer_profile,
        history_limit=history_limit,
    )

    return {
        "file_id": file_container.id,
        "found": True,
        "filename": file_container.filename,
        "viewer_mode": readiness["viewer_mode"],
        "is_viewer_ready": readiness["is_viewer_ready"],
        "geometry_format": readiness.get("geometry_format"),
        "asset_count": len(readiness.get("available_assets", [])),
        "available_assets": readiness.get("available_assets", []),
        "blocking_reasons": readiness.get("blocking_reasons", []),
        "proof": proof,
    }


@file_viewer_router.get("/{file_id}/viewer_readiness")
async def get_viewer_readiness(file_id: str, db: Session = Depends(get_db)):
    """Assess 3D/2D viewer readiness for a file."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    return converter.assess_viewer_readiness(file_container)


@file_viewer_router.get("/{file_id}/geometry/assets")
async def list_geometry_assets(file_id: str, db: Session = Depends(get_db)):
    """List available geometry assets (textures, sidecars) for a file."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    readiness = converter.assess_viewer_readiness(file_container)
    return {
        "file_id": file_id,
        "geometry_format": readiness.get("geometry_format"),
        "assets": readiness.get("available_assets", []),
        "total": len(readiness.get("available_assets", [])),
    }


@file_viewer_router.get("/{file_id}/consumer-summary")
async def get_consumer_summary(
    file_id: str,
    include_audit: bool = Query(False, description="Attach audit proof from CadChangeLog"),
    history_limit: int = Query(
        C11_DEFAULT_AUDIT_HISTORY_LIMIT,
        ge=1,
        le=200,
        description="Max CadChangeLog records when include_audit=true",
    ),
    include_reviewer_profile: bool = Query(
        False,
        description="Resolve reviewer profile from identity database",
    ),
    db: Session = Depends(get_db),
):
    """One-stop consumer-facing summary: readiness + assets + URLs.

    Returns everything a viewer client needs to render or fall back.
    """
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    readiness = converter.assess_viewer_readiness(file_container)
    proof = _build_c11_consumer_proof(
        file_container,
        db=db,
        include_audit=include_audit,
        include_reviewer_profile=include_reviewer_profile,
        history_limit=history_limit,
    )
    return {
        "file_id": file_id,
        "filename": file_container.filename,
        "file_type": file_container.file_type,
        "document_type": file_container.document_type,
        "viewer_mode": readiness["viewer_mode"],
        "is_viewer_ready": readiness["is_viewer_ready"],
        "geometry_format": readiness.get("geometry_format"),
        "assets": readiness.get("available_assets", []),
        "blocking_reasons": readiness.get("blocking_reasons", []),
        "urls": {
            "geometry": f"/api/v1/file/{file_id}/geometry" if readiness["geometry_available"] else None,
            "preview": f"/api/v1/file/{file_id}/preview" if readiness["preview_available"] else None,
            "manifest": f"/api/v1/file/{file_id}/cad_manifest" if readiness["manifest_available"] else None,
            "download": f"/api/v1/file/{file_id}/download",
            "viewer_readiness": f"/api/v1/file/{file_id}/viewer_readiness",
        },
        "proof": proof,
    }


@file_viewer_router.post("/viewer-readiness/export")
async def export_viewer_readiness(
    payload: C11BatchRequest,
    export_format: str = Query("json", description="json|csv"),
    include_audit: bool = Query(False, description="Attach audit proof from CadChangeLog"),
    history_limit: int = Query(
        C11_DEFAULT_AUDIT_HISTORY_LIMIT,
        ge=1,
        le=200,
        description="Max CadChangeLog records when include_audit=true",
    ),
    include_reviewer_profile: bool = Query(
        False,
        description="Resolve reviewer profile from identity database",
    ),
    db: Session = Depends(get_db),
):
    """Export viewer readiness status for a batch of file IDs.

    Accepts ``{"file_ids": ["fc-1", "fc-2", ...]}`` and returns an
    exportable readiness report.
    """
    file_ids = _normalize_batch_file_ids(payload.file_ids)
    normalized_export_format = export_format.strip().lower()

    rows = []
    for fid in file_ids:
        fc = db.get(FileContainer, fid)
        row = _build_c11_export_row(
            fc,
            file_id=fid,
            db=db,
            include_audit=include_audit,
            include_reviewer_profile=include_reviewer_profile,
            history_limit=history_limit,
        )
        rows.append(row)

    if normalized_export_format not in {"json", "csv"}:
        raise HTTPException(
            status_code=400,
            detail="export_format must be one of: json, csv",
        )

    if normalized_export_format == "csv":
        import csv as _csv

        buf = io.StringIO()
        writer = _csv.DictWriter(buf, fieldnames=[
            "file_id", "filename", "found", "viewer_mode", "is_viewer_ready",
            "geometry_format", "asset_count", "blocking_reasons", "review_state",
            "reviewed_by", "reviewed_at", "history_count", "history_latest_action",
        ])
        writer.writeheader()
        for row in rows:
            proof = row.get("proof") or {}
            audit = proof.get("audit") or {}
            reviewed_by = proof.get("review", {}).get("reviewed_by") or {}
            latest_audit = audit.get("latest") or {}
            csv_row = {
                "file_id": row.get("file_id"),
                "filename": row.get("filename"),
                "found": row.get("found"),
                "viewer_mode": row.get("viewer_mode"),
                "is_viewer_ready": row.get("is_viewer_ready"),
                "geometry_format": row.get("geometry_format"),
                "asset_count": row.get("asset_count"),
                "blocking_reasons": ";".join(row.get("blocking_reasons") or []),
                "review_state": (proof.get("review") or {}).get("state"),
                "reviewed_by": reviewed_by.get("id") if isinstance(reviewed_by, dict) else None,
                "reviewed_at": (proof.get("review") or {}).get("reviewed_at"),
                "history_count": audit.get("history_count"),
                "history_latest_action": latest_audit.get("action"),
            }
            writer.writerow(csv_row)
        return StreamingResponse(
            io.BytesIO(buf.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="viewer-readiness.csv"'},
        )

    # Default: JSON
    return {
        "total": len(rows),
        "ready_count": sum(1 for r in rows if r["is_viewer_ready"]),
        "not_ready_count": sum(1 for r in rows if not r["is_viewer_ready"]),
        "not_found_count": sum(1 for r in rows if not r["found"]),
        "requested_file_count": len(file_ids),
        "generated_at": datetime.utcnow().isoformat(),
        "files": rows,
    }


@file_viewer_router.post("/geometry-pack-summary")
async def geometry_pack_summary(
    payload: C11BatchRequest,
    include_audit: bool = Query(False, description="Attach audit proof from CadChangeLog"),
    history_limit: int = Query(
        C11_DEFAULT_AUDIT_HISTORY_LIMIT,
        ge=1,
        le=200,
        description="Max CadChangeLog records when include_audit=true",
    ),
    include_reviewer_profile: bool = Query(
        False,
        description="Resolve reviewer profile from identity database",
    ),
    include_assets: bool = Query(
        True,
        description="Whether to include per-file asset list in pack response",
    ),
    db: Session = Depends(get_db),
):
    """Aggregate geometry asset info for a batch of files.

    Accepts ``{"file_ids": ["fc-1", "fc-2", ...]}`` and returns a
    summary of all geometry assets across those files.
    """
    file_ids = _normalize_batch_file_ids(payload.file_ids)

    converter = CADConverterService(db, vault_base_path=VAULT_DIR)
    items = []
    total_assets = 0
    format_counts: dict = {}
    ready_count = 0
    audited_file_count = 0

    for fid in file_ids:
        fc = db.get(FileContainer, fid)
        if not fc:
            items.append({"file_id": fid, "found": False, "assets": [], "geometry_format": None})
            continue
        readiness = converter.assess_viewer_readiness(fc)
        proof = _build_c11_consumer_proof(
            fc,
            db=db,
            include_audit=include_audit,
            include_reviewer_profile=include_reviewer_profile,
            history_limit=history_limit,
        )
        assets = readiness.get("available_assets", [])
        fmt = readiness.get("geometry_format")
        total_assets += len(assets)
        if fmt:
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        if readiness["is_viewer_ready"]:
            ready_count += 1
        if include_audit and proof.get("audit", {}).get("enabled"):
            audited_file_count += 1
        asset_payload = assets if include_assets else []
        items.append({
            "file_id": fid,
            "found": True,
            "filename": fc.filename,
            "geometry_format": fmt,
            "assets": asset_payload,
            "asset_count": len(assets),
            "is_viewer_ready": readiness["is_viewer_ready"],
            "proof": proof,
        })

    return {
        "total_files": len(file_ids),
        "files_found": sum(1 for i in items if i.get("found", False)),
        "not_found_count": sum(1 for i in items if not i.get("found", False)),
        "viewer_ready_count": ready_count,
        "audited_files": audited_file_count,
        "total_assets": total_assets,
        "format_counts": format_counts,
        "pack": items,
        "generated_at": datetime.utcnow().isoformat(),
    }


@file_viewer_router.get("/{file_id}/geometry")
async def get_geometry(file_id: str, db: Session = Depends(get_db)):
    """Get converted geometry file for 3D viewer."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_container.geometry_path:
        raise HTTPException(status_code=404, detail="Geometry not available")

    media_type = _guess_media_type(file_container.geometry_path)
    return _serve_storage_path(
        file_container.geometry_path, media_type, error_prefix="Geometry"
    )


@file_viewer_router.get("/{file_id}/asset/{asset_name}")
async def get_geometry_asset(
    file_id: str, asset_name: str, db: Session = Depends(get_db)
):
    """Get geometry sidecar asset (e.g., mesh.bin) for glTF."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_container.geometry_path:
        raise HTTPException(status_code=404, detail="Geometry not available")

    safe_name = _sanitize_asset_name(asset_name)
    base_dir = os.path.dirname(file_container.geometry_path)
    asset_path = f"{base_dir}/{safe_name}" if base_dir else safe_name
    media_type = _guess_media_type(asset_path)
    return _serve_storage_path(
        asset_path, media_type, error_prefix="Geometry asset"
    )


@file_viewer_router.get("/{file_id}/cad_asset/{asset_name}", name="get_cad_asset")
async def get_cad_asset(
    file_id: str, asset_name: str, db: Session = Depends(get_db)
):
    """Get CADGF conversion assets (mesh.gltf, mesh.bin, etc.)."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    base_path = file_container.cad_manifest_path or file_container.geometry_path
    if not base_path:
        raise HTTPException(status_code=404, detail="CAD assets not available")

    safe_name = _sanitize_asset_name(asset_name)
    base_dir = os.path.dirname(base_path)
    asset_path = f"{base_dir}/{safe_name}" if base_dir else safe_name

    file_service = FileService()
    if not file_service.file_exists(asset_path):
        raise HTTPException(status_code=404, detail="CAD asset not available")

    media_type = _guess_media_type(asset_path)
    return _serve_storage_path(
        asset_path, media_type, error_prefix="CAD asset"
    )


@file_viewer_router.get("/{file_id}/cad_manifest")
async def get_cad_manifest(
    file_id: str,
    request: Request,
    rewrite: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Get CADGF manifest.json for 2D CAD conversions."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_manifest_path:
        raise HTTPException(status_code=404, detail="CAD manifest not available")
    if not rewrite:
        return _serve_storage_path(
            file_container.cad_manifest_path,
            _guess_media_type(file_container.cad_manifest_path),
            error_prefix="CAD manifest",
        )
    manifest = _load_manifest_payload(file_container)
    manifest = _rewrite_cad_manifest_urls(request, file_container, manifest)
    return JSONResponse(content=manifest)


@file_viewer_router.get("/{file_id}/cad_document")
async def get_cad_document(file_id: str, db: Session = Depends(get_db)):
    """Get CADGF document.json for 2D CAD conversions."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_document_path:
        raise HTTPException(status_code=404, detail="CAD document not available")
    return _serve_storage_path(
        file_container.cad_document_path,
        _guess_media_type(file_container.cad_document_path),
        error_prefix="CAD document",
    )


@file_viewer_router.get("/{file_id}/cad_metadata")
async def get_cad_metadata(file_id: str, db: Session = Depends(get_db)):
    """Get CADGF mesh_metadata.json for 2D CAD conversions."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_metadata_path:
        raise HTTPException(status_code=404, detail="CAD metadata not available")
    return _serve_storage_path(
        file_container.cad_metadata_path,
        _guess_media_type(file_container.cad_metadata_path),
        error_prefix="CAD metadata",
    )


@file_viewer_router.get("/{file_id}/cad_bom")
async def get_cad_bom(file_id: str, db: Session = Depends(get_db)):
    """Get CAD BOM payload (connector-derived)."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_bom_path:
        raise HTTPException(status_code=404, detail="CAD BOM not available")
    return _serve_storage_path(
        file_container.cad_bom_path,
        _guess_media_type(file_container.cad_bom_path),
        error_prefix="CAD BOM",
    )


@file_viewer_router.get("/{file_id}/cad_dedup")
async def get_cad_dedup(file_id: str, db: Session = Depends(get_db)):
    """Get CAD dedup similarity payload (DedupCAD Vision)."""
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_dedup_path:
        raise HTTPException(status_code=404, detail="CAD dedup not available")
    return _serve_storage_path(
        file_container.cad_dedup_path,
        _guess_media_type(file_container.cad_dedup_path),
        error_prefix="CAD dedup",
    )
