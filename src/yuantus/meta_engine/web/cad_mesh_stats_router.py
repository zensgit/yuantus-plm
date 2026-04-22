from __future__ import annotations

import io
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.database import get_db
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.services.file_service import FileService

cad_mesh_stats_router = APIRouter(prefix="/cad", tags=["CAD"])


class CadMeshStatsResponse(BaseModel):
    file_id: str
    stats: Dict[str, Any]


def _load_cad_metadata_payload(file_container: FileContainer) -> Optional[Dict[str, Any]]:
    if not file_container.cad_metadata_path:
        return None
    file_service = FileService()
    output_stream = io.BytesIO()
    try:
        file_service.download_file(file_container.cad_metadata_path, output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"CAD metadata download failed: {exc}"
        ) from exc
    output_stream.seek(0)
    try:
        payload = json.load(output_stream)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="CAD metadata invalid JSON"
        ) from exc
    return payload if isinstance(payload, dict) else None


def _extract_mesh_stats(payload: Dict[str, Any]) -> Dict[str, Any]:
    stats: Dict[str, Any] = {"raw_keys": sorted(payload.keys())}
    entities = payload.get("entities")
    if isinstance(entities, list):
        stats["entity_count"] = len(entities)
    for key in ("triangle_count", "triangles", "face_count", "faces"):
        value = payload.get(key)
        if isinstance(value, int):
            stats["triangle_count"] = value
            break
        if isinstance(value, list):
            stats["triangle_count"] = len(value)
            break
    bounds = payload.get("bounds") or payload.get("bbox")
    if bounds is not None:
        stats["bounds"] = bounds
    return stats


@cad_mesh_stats_router.get(
    "/files/{file_id}/mesh-stats", response_model=CadMeshStatsResponse
)
def get_cad_mesh_stats(
    file_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadMeshStatsResponse:
    file_container = db.get(FileContainer, file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_container.cad_metadata_path:
        return CadMeshStatsResponse(
            file_id=file_container.id,
            stats={
                "available": False,
                "reason": "CAD metadata not available",
            },
        )

    payload = _load_cad_metadata_payload(file_container)
    if not payload or payload.get("kind") == "cad_attributes":
        return CadMeshStatsResponse(
            file_id=file_container.id,
            stats={
                "available": False,
                "reason": "CAD mesh metadata not available",
            },
        )
    if not any(
        key in payload
        for key in (
            "entities",
            "triangle_count",
            "triangles",
            "face_count",
            "faces",
            "bounds",
            "bbox",
        )
    ):
        return CadMeshStatsResponse(
            file_id=file_container.id,
            stats={
                "available": False,
                "reason": "CAD mesh metadata not available",
                "raw_keys": sorted(payload.keys()),
            },
        )
    stats = _extract_mesh_stats(payload or {})
    stats.setdefault("available", True)
    return CadMeshStatsResponse(file_id=file_container.id, stats=stats)
