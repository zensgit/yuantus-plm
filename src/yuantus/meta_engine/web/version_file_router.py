"""Version file API endpoints."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional as get_current_user_id
from yuantus.database import get_db
from yuantus.meta_engine.version.file_service import (
    VersionFileError,
    VersionFileService,
)
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.version.service import VersionError, VersionService

version_file_router = APIRouter(prefix="/versions", tags=["Versioning"])


class AttachFileRequest(BaseModel):
    file_id: str
    file_role: str = "attachment"
    is_primary: bool = False
    sequence: int = 0


class SetPrimaryRequest(BaseModel):
    file_id: str
    file_role: Optional[str] = None


class SetThumbnailRequest(BaseModel):
    thumbnail_data: str  # Base64 encoded


def _ensure_version_file_editable(
    version: ItemVersion,
    user_id: int,
    *,
    require_checkout: bool = True,
) -> None:
    if version.is_released:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version.id} is released and locked",
        )
    if require_checkout and not version.checked_out_by_id:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version.id} must be checked out before editing files",
        )
    if version.checked_out_by_id and version.checked_out_by_id != user_id:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version.id} is checked out by another user",
        )


def _raise_version_file_http_error(exc: VersionFileError) -> None:
    detail = str(exc)
    lower = detail.lower()
    if "not found" in lower or "not attached" in lower:
        raise HTTPException(status_code=404, detail=detail)
    if (
        "checked out" in lower
        or "released" in lower
        or "locked" in lower
    ):
        raise HTTPException(status_code=409, detail=detail)
    raise HTTPException(status_code=400, detail=detail)


@version_file_router.get("/{version_id}/detail")
def get_version_detail(version_id: str, db: Session = Depends(get_db)):
    """Get complete version information including files."""
    file_service = VersionFileService(db)
    try:
        return file_service.get_version_detail(version_id)
    except VersionFileError as e:
        raise HTTPException(status_code=404, detail=str(e))


@version_file_router.post("/{version_id}/files")
def attach_file_to_version(
    version_id: str,
    request: AttachFileRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Attach a file to a version."""
    file_service = VersionFileService(db)
    try:
        version = db.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")
        _ensure_version_file_editable(version, user_id)
        vf = file_service.attach_file(
            version_id=version_id,
            file_id=request.file_id,
            file_role=request.file_role,
            is_primary=request.is_primary,
            sequence=request.sequence,
            user_id=user_id,
        )
        db.commit()
        return {
            "id": vf.id,
            "version_id": vf.version_id,
            "file_id": vf.file_id,
            "file_role": vf.file_role,
            "is_primary": vf.is_primary,
        }
    except VersionFileError as e:
        db.rollback()
        _raise_version_file_http_error(e)


@version_file_router.delete("/{version_id}/files/{file_id}")
def detach_file_from_version(
    version_id: str,
    file_id: str,
    file_role: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Detach a file from a version."""
    version = db.get(ItemVersion, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    _ensure_version_file_editable(version, user_id)
    file_service = VersionFileService(db)
    try:
        success = file_service.detach_file(
            version_id,
            file_id,
            file_role,
            user_id=user_id,
        )
        if not success:
            raise HTTPException(status_code=404, detail="File not attached to version")
        db.commit()
        return {"status": "detached"}
    except VersionFileError as e:
        db.rollback()
        _raise_version_file_http_error(e)


@version_file_router.get("/{version_id}/files")
def get_version_files(
    version_id: str, role: Optional[str] = None, db: Session = Depends(get_db)
):
    """Get all files attached to a version."""
    file_service = VersionFileService(db)
    files = file_service.get_version_files(version_id, role)
    return [
        {
            "id": vf.id,
            "file_id": vf.file_id,
            "file_role": vf.file_role,
            "sequence": vf.sequence,
            "is_primary": vf.is_primary,
            "checked_out_by_id": vf.checked_out_by_id,
            "checked_out_at": (
                vf.checked_out_at.isoformat() if vf.checked_out_at else None
            ),
            "filename": vf.file.filename if vf.file else None,
            "file_type": vf.file.file_type if vf.file else None,
            "file_size": vf.file.file_size if vf.file else None,
        }
        for vf in files
    ]


@version_file_router.post("/{version_id}/files/{file_id}/checkout")
def checkout_version_file(
    version_id: str,
    file_id: str,
    file_role: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    file_service = VersionFileService(db)
    try:
        vf = file_service.checkout_file(
            version_id,
            file_id,
            user_id,
            file_role=file_role,
        )
        db.commit()
        return {
            "id": vf.id,
            "version_id": vf.version_id,
            "file_id": vf.file_id,
            "file_role": vf.file_role,
            "checked_out_by_id": vf.checked_out_by_id,
            "checked_out_at": (
                vf.checked_out_at.isoformat() if vf.checked_out_at else None
            ),
        }
    except VersionFileError as e:
        db.rollback()
        _raise_version_file_http_error(e)


@version_file_router.post("/{version_id}/files/{file_id}/undo-checkout")
def undo_checkout_version_file(
    version_id: str,
    file_id: str,
    file_role: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    file_service = VersionFileService(db)
    try:
        vf = file_service.undo_checkout_file(
            version_id,
            file_id,
            user_id,
            file_role=file_role,
        )
        db.commit()
        return {
            "id": vf.id,
            "version_id": vf.version_id,
            "file_id": vf.file_id,
            "file_role": vf.file_role,
            "checked_out_by_id": vf.checked_out_by_id,
            "checked_out_at": (
                vf.checked_out_at.isoformat() if vf.checked_out_at else None
            ),
        }
    except VersionFileError as e:
        db.rollback()
        _raise_version_file_http_error(e)


@version_file_router.get("/{version_id}/files/{file_id}/lock")
def get_version_file_lock(
    version_id: str,
    file_id: str,
    file_role: Optional[str] = None,
    db: Session = Depends(get_db),
):
    file_service = VersionFileService(db)
    try:
        return file_service.get_file_lock(
            version_id,
            file_id,
            file_role=file_role,
        )
    except VersionFileError as e:
        _raise_version_file_http_error(e)


@version_file_router.put("/{version_id}/files/primary")
def set_primary_file(
    version_id: str,
    request: SetPrimaryRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Set a file as the primary file for a version."""
    file_service = VersionFileService(db)
    try:
        version = db.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")
        _ensure_version_file_editable(version, user_id)
        vf = file_service.set_primary_file(
            version_id,
            request.file_id,
            user_id=user_id,
            file_role=request.file_role,
        )
        db.commit()
        return {"id": vf.id, "file_id": vf.file_id, "is_primary": vf.is_primary}
    except VersionFileError as e:
        db.rollback()
        _raise_version_file_http_error(e)


@version_file_router.put("/{version_id}/thumbnail")
def set_version_thumbnail(
    version_id: str,
    request: SetThumbnailRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Set the thumbnail for a version."""
    file_service = VersionFileService(db)
    try:
        version = db.get(ItemVersion, version_id)
        if not version:
            raise VersionFileError(f"Version {version_id} not found")
        _ensure_version_file_editable(version, user_id)
        version = file_service.set_thumbnail(version_id, request.thumbnail_data)
        db.commit()
        return {"status": "updated", "version_id": version.id}
    except VersionFileError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@version_file_router.get("/compare-full")
def compare_versions_full(v1: str, v2: str, db: Session = Depends(get_db)):
    """
    Full comparison of two versions including properties and files.
    """
    version_service = VersionService(db)
    file_service = VersionFileService(db)

    try:
        prop_diff = version_service.compare_versions(v1, v2)
        file_diff = file_service.compare_version_files(v1, v2)
        return {"property_comparison": prop_diff, "file_comparison": file_diff}
    except (VersionError, VersionFileError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@version_file_router.get("/items/{item_id}/tree-full")
def get_version_tree_full(item_id: str, db: Session = Depends(get_db)):
    """
    Get version tree with file counts and thumbnails.
    """
    version_service = VersionService(db)
    tree = version_service.get_version_tree(item_id)

    for node in tree:
        version = db.get(ItemVersion, node["id"])
        if version:
            node["file_count"] = version.file_count or 0
            node["thumbnail"] = version.thumbnail_data
            node["primary_file_id"] = version.primary_file_id

    return tree
