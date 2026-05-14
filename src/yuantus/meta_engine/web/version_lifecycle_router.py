"""Version lifecycle API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import get_current_user_id_optional as get_current_user_id
from yuantus.database import get_db
from yuantus.meta_engine.services.parallel_tasks_service import DocumentMultiSiteService
from yuantus.meta_engine.version.models import ItemVersion
from yuantus.meta_engine.version.service import VersionError, VersionService

version_lifecycle_router = APIRouter(prefix="/versions", tags=["Versioning"])


def _raise_version_http_error(exc: VersionError) -> None:
    detail = str(exc)
    lower = detail.lower()
    if "not found" in lower:
        raise HTTPException(status_code=404, detail=detail) from exc
    if (
        "checked out" in lower
        or "locked" in lower
        or "file-level lock" in lower
        or "locks held" in lower
    ):
        raise HTTPException(status_code=409, detail=detail) from exc
    raise HTTPException(status_code=400, detail=detail) from exc


@version_lifecycle_router.post("/items/{item_id}/init")
def create_initial_version(
    item_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    from yuantus.meta_engine.models.item import Item

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        ver = service.create_initial_version(item, user_id)
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


@version_lifecycle_router.post("/items/{item_id}/checkout")
def checkout(
    item_id: str,
    response: Response,
    user_id: int = Depends(get_current_user_id),
    comment: Optional[str] = Body(None),
    version_id: Optional[str] = Body(None),
    doc_sync_site_id: Optional[str] = Body(None),
    doc_sync_direction: Optional[str] = Body(None),
    doc_sync_gate_mode: str = Body("block"),
    doc_sync_direction_thresholds: Optional[Dict[str, Dict[str, int]]] = Body(None),
    doc_sync_document_ids: Optional[List[str]] = Body(None),
    doc_sync_window_days: int = Body(7),
    doc_sync_limit: int = Body(200),
    doc_sync_block_on_dead_letter_only: bool = Body(False),
    doc_sync_max_pending: int = Body(0),
    doc_sync_max_processing: int = Body(0),
    doc_sync_max_failed: int = Body(0),
    doc_sync_max_dead_letter: int = Body(0),
    db: Session = Depends(get_db),
):
    if doc_sync_site_id:
        gate_document_ids = {
            str(doc_id).strip()
            for doc_id in (doc_sync_document_ids or [])
            if str(doc_id).strip()
        }
        normalized_version_id = str(version_id or "").strip() or None
        if normalized_version_id:
            gate_document_ids.add(normalized_version_id)
            version = db.get(ItemVersion, normalized_version_id)
            if version and str(version.item_id or "") == str(item_id):
                if version.primary_file_id:
                    gate_document_ids.add(str(version.primary_file_id).strip())
                for version_file in version.version_files or []:
                    file_id = str(getattr(version_file, "file_id", "") or "").strip()
                    if file_id:
                        gate_document_ids.add(file_id)
        if not gate_document_ids:
            gate_document_ids.add(str(item_id).strip())

        doc_sync_service = DocumentMultiSiteService(db)
        try:
            gate = doc_sync_service.evaluate_checkout_sync_gate(
                item_id=item_id,
                site_id=doc_sync_site_id,
                direction=doc_sync_direction,
                mode=doc_sync_gate_mode,
                direction_thresholds=doc_sync_direction_thresholds,
                version_id=normalized_version_id,
                document_ids=sorted(gate_document_ids),
                window_days=doc_sync_window_days,
                limit=doc_sync_limit,
                block_on_dead_letter_only=doc_sync_block_on_dead_letter_only,
                max_pending=doc_sync_max_pending,
                max_processing=doc_sync_max_processing,
                max_failed=doc_sync_max_failed,
                max_dead_letter=doc_sync_max_dead_letter,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "doc_sync_checkout_gate_invalid",
                    "message": str(exc),
                    "context": {
                        "item_id": item_id,
                        "site_id": doc_sync_site_id,
                        "gate_mode": doc_sync_gate_mode,
                        "direction_thresholds": doc_sync_direction_thresholds,
                        "window_days": doc_sync_window_days,
                        "limit": doc_sync_limit,
                        "block_on_dead_letter_only": doc_sync_block_on_dead_letter_only,
                        "max_pending": doc_sync_max_pending,
                        "max_processing": doc_sync_max_processing,
                        "max_failed": doc_sync_max_failed,
                        "max_dead_letter": doc_sync_max_dead_letter,
                    },
                },
            )
        if gate.get("blocking"):
            block_on_dead_letter_only = bool(
                (gate.get("policy") or {}).get("block_on_dead_letter_only")
            )
            message = "Checkout blocked by doc-sync backlog"
            if block_on_dead_letter_only:
                message = "Checkout blocked by doc-sync dead-letter backlog"
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "doc_sync_checkout_blocked",
                    "message": message,
                    "context": gate,
                },
            )
        if gate.get("warning"):
            response.headers["X-Doc-Sync-Gate-Verdict"] = str(
                gate.get("verdict") or "warn"
            )
            response.headers["X-Doc-Sync-Gate-Threshold-Hits"] = str(
                len(gate.get("blocking_reasons") or [])
            )

    service = VersionService(db)
    try:
        ver = service.checkout(item_id, user_id, comment, version_id)
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        _raise_version_http_error(e)


@version_lifecycle_router.post("/items/{item_id}/checkin")
def checkin(
    item_id: str,
    user_id: int = Depends(get_current_user_id),
    comment: Optional[str] = Body(None),
    properties: Optional[Dict[str, Any]] = Body(None),
    version_id: Optional[str] = Body(None),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    try:
        ver = service.checkin(item_id, user_id, properties, comment, version_id)
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        _raise_version_http_error(e)


@version_lifecycle_router.post("/items/{item_id}/merge")
def merge_branch(
    item_id: str,
    source_version_id: str = Body(..., embed=True),
    target_version_id: str = Body(..., embed=True),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    try:
        ver = service.merge_branch(
            item_id, source_version_id, target_version_id, user_id
        )
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        _raise_version_http_error(e)


@version_lifecycle_router.get("/compare")
def compare_versions(v1: str, v2: str, db: Session = Depends(get_db)):
    service = VersionService(db)
    try:
        return service.compare_versions(v1, v2)
    except VersionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@version_lifecycle_router.post("/items/{item_id}/revise")
def revise(
    item_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    try:
        ver = service.revise(item_id, user_id)
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        _raise_version_http_error(e)


@version_lifecycle_router.get("/items/{item_id}/history")
def get_history(item_id: str, db: Session = Depends(get_db)):
    service = VersionService(db)
    return service.get_history(item_id)


@version_lifecycle_router.post("/items/{item_id}/branch")
def create_branch(
    item_id: str,
    source_version_id: str = Body(..., embed=True),
    branch_name: str = Body(..., embed=True),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    try:
        ver = service.create_branch(item_id, source_version_id, branch_name, user_id)
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        _raise_version_http_error(e)
