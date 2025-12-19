from __future__ import annotations

import io
import os
from pathlib import Path
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.database import get_db

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.meta_engine.models.file import FileContainer, FileRole, ItemFile
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.file_service import FileService
from yuantus.meta_engine.services.job_service import JobService
from yuantus.meta_engine.services.checkin_service import CheckinManager

router = APIRouter(prefix="/cad", tags=["CAD"])

"""
CAD Connector API
Handles Document Locking and Versioning.
"""


def get_checkin_manager(
    user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> CheckinManager:
    # RBACUser should have an integer ID map?
    # user.id is the key (99, 1, 2)
    return CheckinManager(db, user_id=user.id)


class CadImportJob(BaseModel):
    id: str
    task_type: str
    status: str


class CadImportResponse(BaseModel):
    file_id: str
    filename: str
    checksum: str
    is_duplicate: bool
    item_id: Optional[str] = None
    attachment_id: Optional[str] = None
    jobs: List[CadImportJob] = Field(default_factory=list)
    download_url: str
    preview_url: Optional[str] = None
    geometry_url: Optional[str] = None


def _calculate_checksum(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()


def _get_mime_type(filename: str) -> str:
    import mimetypes

    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def _get_document_type(extension: str) -> str:
    ext = extension.lower().lstrip(".")
    if ext in {"dwg", "dxf", "pdf"}:
        return "2d"
    if ext in {"step", "stp", "iges", "igs", "stl", "obj", "gltf", "glb"}:
        return "3d"
    return "other"


def _get_cad_format(extension: str) -> Optional[str]:
    ext = extension.lower().lstrip(".")
    cad_formats = {
        "step": "STEP",
        "stp": "STEP",
        "iges": "IGES",
        "igs": "IGES",
        "sldprt": "SOLIDWORKS",
        "sldasm": "SOLIDWORKS",
        "ipt": "INVENTOR",
        "iam": "INVENTOR",
        "prt": "NX_OR_PROE",
        "asm": "NX_OR_PROE",
        "catpart": "CATIA",
        "catproduct": "CATIA",
        "par": "SOLID_EDGE",
        "psm": "SOLID_EDGE",
        "3dm": "RHINO",
        "dwg": "AUTOCAD",
        "dxf": "AUTOCAD",
        "stl": "STL",
        "obj": "OBJ",
        "gltf": "GLTF",
        "glb": "GLTF",
        "pdf": "PDF",
    }
    return cad_formats.get(ext)


@router.post("/import", response_model=CadImportResponse)
async def import_cad(
    file: UploadFile = File(...),
    item_id: Optional[str] = Form(default=None, description="Attach to an existing item id"),
    file_role: str = Form(default=FileRole.NATIVE_CAD.value, description="Attachment role"),
    create_preview_job: bool = Form(default=True),
    create_geometry_job: bool = Form(default=False),
    geometry_format: str = Form(default="gltf", description="obj|gltf|glb|stl"),
    create_dedup_job: bool = Form(default=True),
    dedup_mode: str = Form(default="balanced", description="fast|balanced|precise"),
    create_ml_job: bool = Form(default=False, description="Call cad-ml-platform vision analyze"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CadImportResponse:
    """
    Import a CAD file: upload to storage, optionally attach to an item, then enqueue pipeline jobs.

    Jobs are created in `meta_conversion_jobs` and executed by `yuantus worker`.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    checksum = _calculate_checksum(content)
    existing = db.query(FileContainer).filter(FileContainer.checksum == checksum).first()
    is_duplicate = existing is not None

    file_container: FileContainer
    if existing:
        file_container = existing
    else:
        file_id = str(uuid.uuid4())
        ext = Path(file.filename).suffix.lower()
        stored_filename = f"{file_id}{ext}"
        type_dir = _get_document_type(ext)
        storage_key = f"{type_dir}/{file_id[:2]}/{stored_filename}"

        file_service = FileService()
        file_service.upload_file(io.BytesIO(content), storage_key)

        file_container = FileContainer(
            id=file_id,
            filename=file.filename,
            file_type=ext.lstrip("."),
            mime_type=_get_mime_type(file.filename),
            file_size=len(content),
            checksum=checksum,
            system_path=storage_key,
            document_type=_get_document_type(ext),
            is_native_cad=_get_cad_format(ext) is not None,
            cad_format=_get_cad_format(ext),
            created_by_id=user.id,
        )
        db.add(file_container)
        db.commit()

    attachment_id: Optional[str] = None
    if item_id:
        item = db.get(Item, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        if item.current_version_id:
            from yuantus.meta_engine.version.models import ItemVersion

            ver = db.get(ItemVersion, item.current_version_id)
            if ver and ver.checked_out_by_id and ver.checked_out_by_id != user.id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Version {ver.id} is checked out by another user",
                )

        existing_link = (
            db.query(ItemFile)
            .filter(ItemFile.item_id == item_id, ItemFile.file_id == file_container.id)
            .first()
        )
        if existing_link:
            existing_link.file_role = file_role
            db.add(existing_link)
            db.commit()
            attachment_id = existing_link.id
        else:
            link = ItemFile(
                item_id=item_id,
                file_id=file_container.id,
                file_role=file_role,
            )
            db.add(link)
            db.commit()
            attachment_id = link.id

    jobs: List[CadImportJob] = []
    job_service = JobService(db)

    def _enqueue(task_type: str, payload: Dict[str, Any], priority: int) -> None:
        if item_id:
            payload = {**payload, "item_id": item_id}
        job = job_service.create_job(task_type=task_type, payload=payload, user_id=user.id, priority=priority)
        jobs.append(CadImportJob(id=job.id, task_type=job.task_type, status=job.status))

    # Pipeline: preview -> geometry -> dedup -> ml
    if create_preview_job and file_container.is_cad_file():
        _enqueue("cad_preview", {"file_id": file_container.id}, priority=10)

    if create_geometry_job and file_container.is_cad_file():
        _enqueue(
            "cad_geometry",
            {"file_id": file_container.id, "target_format": geometry_format},
            priority=20,
        )

    # Dedup is most relevant for 2D drawings; keep it optional.
    if create_dedup_job and file_container.file_type in {"dwg", "dxf", "pdf", "png", "jpg", "jpeg"}:
        _enqueue(
            "cad_dedup_vision",
            {"file_id": file_container.id, "mode": dedup_mode, "user_name": user.username},
            priority=30,
        )

    if create_ml_job and file_container.file_type in {"pdf", "png", "jpg", "jpeg", "dwg", "dxf"}:
        _enqueue(
            "cad_ml_vision",
            {"file_id": file_container.id},
            priority=40,
        )

    preview_url = f"/api/v1/file/{file_container.id}/preview" if file_container.preview_path else None
    geometry_url = f"/api/v1/file/{file_container.id}/geometry" if file_container.geometry_path else None
    return CadImportResponse(
        file_id=file_container.id,
        filename=file_container.filename,
        checksum=file_container.checksum,
        is_duplicate=is_duplicate,
        item_id=item_id,
        attachment_id=attachment_id,
        jobs=jobs,
        download_url=f"/api/v1/file/{file_container.id}/download",
        preview_url=preview_url,
        geometry_url=geometry_url,
    )


@router.post("/{item_id}/checkout")
def checkout_document(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    """
    Lock a document for editing.
    """
    try:
        item = mgr.checkout(item_id)
        # Commit handled by service or need manual commit?
        # Service flushes, but typically Router/Dependencies commit.
        # But CheckinManager commits/flushes?
        # CheckinManager.checkout does 'add' and 'flush'.
        # We need final commit.
        mgr.session.commit()
        return {
            "status": "success",
            "message": "Item locked.",
            "locked_by_id": item.locked_by_id,
        }
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        mgr.session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{item_id}/undo-checkout")
def undo_checkout(
    item_id: str, mgr: CheckinManager = Depends(get_checkin_manager)
) -> Any:
    try:
        mgr.undo_checkout(item_id)
        mgr.session.commit()
        return {"status": "success", "message": "Item unlocked."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{item_id}/checkin")
def checkin_document(
    item_id: str,
    file: UploadFile = File(...),
    mgr: CheckinManager = Depends(get_checkin_manager),
) -> Any:
    """
    Upload new file version and unlock.
    """
    try:
        content = file.file.read()
        filename = file.filename

        new_item = mgr.checkin(item_id, content, filename)
        mgr.session.commit()

        return {
            "status": "success",
            "new_item_id": new_item.id,
            "generation": new_item.generation,
        }
    except ValueError as e:
        mgr.session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        mgr.session.rollback()
        # Log error
        raise HTTPException(status_code=500, detail=str(e))
