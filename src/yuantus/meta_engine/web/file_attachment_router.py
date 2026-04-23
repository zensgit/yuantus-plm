"""
File attachment router.

This module owns item-file association endpoints split out of the legacy file
router.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional
from yuantus.database import get_db
from yuantus.meta_engine.lifecycle.guard import is_item_locked
from yuantus.meta_engine.models.file import FileContainer, FileRole, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.version.file_service import VersionFileError, VersionFileService


file_attachment_router = APIRouter(prefix="/file", tags=["File Management"])


class AttachFileRequest(BaseModel):
    """Request to attach file to item."""

    item_id: str
    file_id: str
    file_role: str = FileRole.ATTACHMENT.value
    description: Optional[str] = None


def _ensure_current_version_attachment_editable(
    db: Session,
    item: Optional[Item],
    *,
    file_id: str,
    file_role: str,
    user_id: int,
) -> None:
    if not item or not item.current_version_id:
        return

    from yuantus.meta_engine.version.models import ItemVersion

    version = db.get(ItemVersion, item.current_version_id)
    if not version:
        return

    if version.checked_out_by_id and version.checked_out_by_id != user_id:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version.id} is checked out by another user",
        )

    vf_service = VersionFileService(db)
    try:
        vf_service.ensure_file_editable(
            version.id,
            file_id,
            user_id,
            file_role=file_role,
        )
    except VersionFileError as exc:
        detail = str(exc)
        lower = detail.lower()
        if "is not attached to version" in lower:
            return
        if (
            "checked out" in lower
            or "locked" in lower
            or "released" in lower
            or "specify file_role" in lower
        ):
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


@file_attachment_router.post("/attach")
async def attach_file_to_item(
    request: AttachFileRequest,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """
    Attach a file to an item with a specific role.

    Based on DocDoku PartIteration pattern (nativeCADFile, attachedFiles, geometries).
    """
    item = db.get(Item, request.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item_type = db.get(ItemType, item.item_type_id)
    locked, locked_state = is_item_locked(db, item, item_type)
    if locked:
        raise HTTPException(
            status_code=409,
            detail=f"Item is locked in state '{locked_state or item.state}'",
        )

    file_container = db.get(FileContainer, request.file_id)
    if not file_container:
        raise HTTPException(status_code=404, detail="File not found")

    existing = (
        db.query(ItemFile)
        .filter(
            ItemFile.item_id == request.item_id,
            ItemFile.file_id == request.file_id,
        )
        .first()
    )
    if existing:
        _ensure_current_version_attachment_editable(
            db,
            item,
            file_id=existing.file_id,
            file_role=existing.file_role,
            user_id=user_id,
        )
        if request.file_role != existing.file_role:
            _ensure_current_version_attachment_editable(
                db,
                item,
                file_id=existing.file_id,
                file_role=request.file_role,
                user_id=user_id,
            )
        if existing.file_role != request.file_role:
            existing.file_role = request.file_role
            existing.description = request.description
            db.commit()
        return {"status": "updated", "id": existing.id}

    _ensure_current_version_attachment_editable(
        db,
        item,
        file_id=request.file_id,
        file_role=request.file_role,
        user_id=user_id,
    )

    item_file = ItemFile(
        id=str(uuid.uuid4()),
        item_id=request.item_id,
        file_id=request.file_id,
        file_role=request.file_role,
        description=request.description,
    )
    db.add(item_file)
    db.commit()

    return {"status": "created", "id": item_file.id}


@file_attachment_router.get("/item/{item_id}")
async def get_item_files(
    item_id: str,
    role: Optional[str] = Query(None, description="Filter by file role"),
    db: Session = Depends(get_db),
):
    """Get all files attached to an item."""
    query = db.query(ItemFile).filter(ItemFile.item_id == item_id)
    if role:
        query = query.filter(ItemFile.file_role == role)

    item_files = query.order_by(ItemFile.sequence.asc()).all()

    result = []
    for item_file in item_files:
        file_container = db.get(FileContainer, item_file.file_id)
        if file_container:
            result.append(
                {
                    "id": item_file.id,
                    "file_id": file_container.id,
                    "filename": file_container.filename,
                    "file_role": item_file.file_role,
                    "description": item_file.description,
                    "file_type": file_container.file_type,
                    "file_size": file_container.file_size,
                    "document_type": file_container.document_type,
                    "author": file_container.author,
                    "source_system": file_container.source_system,
                    "source_version": file_container.source_version,
                    "document_version": file_container.document_version,
                    "preview_url": (
                        f"/api/v1/file/{file_container.id}/preview"
                        if file_container.preview_path
                        else None
                    ),
                    "download_url": f"/api/v1/file/{file_container.id}/download",
                }
            )

    return result


@file_attachment_router.delete("/attachment/{attachment_id}")
async def detach_file(
    attachment_id: str,
    user_id: int = Depends(get_current_user_id_optional),
    db: Session = Depends(get_db),
):
    """Remove file attachment from item."""
    item_file = db.get(ItemFile, attachment_id)
    if not item_file:
        raise HTTPException(status_code=404, detail="Attachment not found")

    item = db.get(Item, item_file.item_id)
    if item:
        item_type = db.get(ItemType, item.item_type_id)
        locked, locked_state = is_item_locked(db, item, item_type)
        if locked:
            raise HTTPException(
                status_code=409,
                detail=f"Item is locked in state '{locked_state or item.state}'",
            )
    _ensure_current_version_attachment_editable(
        db,
        item,
        file_id=item_file.file_id,
        file_role=item_file.file_role,
        user_id=user_id,
    )

    db.delete(item_file)
    db.commit()

    return {"status": "deleted"}
