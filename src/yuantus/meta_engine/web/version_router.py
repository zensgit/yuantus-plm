from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from yuantus.database import get_db
from yuantus.meta_engine.version.service import (
    VersionService,
    VersionError,
    IterationService,
    RevisionSchemeService,
)
from yuantus.meta_engine.version.file_service import (
    VersionFileService,
    VersionFileError,
)
from yuantus.meta_engine.version.models import ItemVersion

from yuantus.api.dependencies.auth import get_current_user_id_optional as get_current_user_id


version_router = APIRouter(prefix="/versions", tags=["Versioning"])


# ===============================
# Pydantic Models for Sprint 2
# ===============================


class AttachFileRequest(BaseModel):
    file_id: str
    file_role: str = "attachment"
    is_primary: bool = False
    sequence: int = 0


class SetPrimaryRequest(BaseModel):
    file_id: str


class SetThumbnailRequest(BaseModel):
    thumbnail_data: str  # Base64 encoded


# ===============================
# Service Helpers
# ===============================


def get_service(db: Session = Depends(get_db)) -> VersionService:
    return VersionService(db)


def get_file_service(db: Session = Depends(get_db)) -> VersionFileService:
    return VersionFileService(db)


def _ensure_version_file_editable(version: ItemVersion, user_id: int) -> None:
    if version.checked_out_by_id and version.checked_out_by_id != user_id:
        raise HTTPException(
            status_code=409,
            detail=f"Version {version.id} is checked out by another user",
        )


@version_router.post("/items/{item_id}/init")
def create_initial_version(
    item_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    # Ideally fetch item first or let service handle
    # Service needs Item object
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
        raise HTTPException(status_code=400, detail=str(e))


@version_router.post("/items/{item_id}/checkout")
def checkout(
    item_id: str,
    user_id: int = Depends(get_current_user_id),
    comment: Optional[str] = Body(None),
    version_id: Optional[str] = Body(None),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    try:
        ver = service.checkout(item_id, user_id, comment, version_id)
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@version_router.post("/items/{item_id}/checkin")
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
        raise HTTPException(status_code=400, detail=str(e))


# ... existing endpoints ...


@version_router.post("/items/{item_id}/merge")
def merge_branch(
    item_id: str,
    source_version_id: str = Body(..., embed=True),
    target_version_id: str = Body(..., embed=True),
    user_id: int = Body(1, embed=True),
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
        raise HTTPException(status_code=400, detail=str(e))


@version_router.get("/compare")
def compare_versions(v1: str, v2: str, db: Session = Depends(get_db)):
    service = VersionService(db)
    try:
        return service.compare_versions(v1, v2)
    except VersionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@version_router.post("/items/{item_id}/revise")
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
        raise HTTPException(status_code=400, detail=str(e))


@version_router.get("/items/{item_id}/history")
def get_history(item_id: str, db: Session = Depends(get_db)):
    service = VersionService(db)
    return service.get_history(item_id)


@version_router.post("/{version_id}/effectivity")
def add_effectivity(
    version_id: str,
    start_date: datetime = Body(...),
    end_date: Optional[datetime] = Body(None),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    eff = service.add_date_effectivity(version_id, start_date, end_date)
    db.commit()
    return eff


@version_router.get("/items/{item_id}/effective")
def get_effective_version(
    item_id: str, date: datetime = None, db: Session = Depends(get_db)
):
    if not date:
        date = datetime.utcnow()
    service = VersionService(db)
    ver = service.find_effective_version(item_id, date)
    if not ver:
        raise HTTPException(status_code=404, detail="No effective version found")
    return ver


@version_router.post("/items/{item_id}/branch")
def create_branch(
    item_id: str,
    source_version_id: str = Body(..., embed=True),
    branch_name: str = Body(..., embed=True),
    user_id: int = Body(1, embed=True),
    db: Session = Depends(get_db),
):
    service = VersionService(db)
    try:
        ver = service.create_branch(item_id, source_version_id, branch_name, user_id)
        db.commit()
        return ver
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@version_router.get("/items/{item_id}/tree")
def get_version_tree(item_id: str, db: Session = Depends(get_db)):
    service = VersionService(db)
    return service.get_version_tree(item_id)


# ===============================
# Sprint 2: Version File Endpoints
# ===============================


@version_router.get("/{version_id}/detail")
def get_version_detail(version_id: str, db: Session = Depends(get_db)):
    """Get complete version information including files."""
    file_service = VersionFileService(db)
    try:
        return file_service.get_version_detail(version_id)
    except VersionFileError as e:
        raise HTTPException(status_code=404, detail=str(e))


@version_router.post("/{version_id}/files")
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
        raise HTTPException(status_code=400, detail=str(e))


@version_router.delete("/{version_id}/files/{file_id}")
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
    success = file_service.detach_file(version_id, file_id, file_role)
    if not success:
        raise HTTPException(status_code=404, detail="File not attached to version")
    db.commit()
    return {"status": "detached"}


@version_router.get("/{version_id}/files")
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
            "filename": vf.file.filename if vf.file else None,
            "file_type": vf.file.file_type if vf.file else None,
            "file_size": vf.file.file_size if vf.file else None,
        }
        for vf in files
    ]


@version_router.put("/{version_id}/files/primary")
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
        vf = file_service.set_primary_file(version_id, request.file_id)
        db.commit()
        return {"id": vf.id, "file_id": vf.file_id, "is_primary": vf.is_primary}
    except VersionFileError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@version_router.put("/{version_id}/thumbnail")
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


@version_router.get("/compare-full")
def compare_versions_full(v1: str, v2: str, db: Session = Depends(get_db)):
    """
    Full comparison of two versions including properties and files.
    """
    version_service = VersionService(db)
    file_service = VersionFileService(db)

    try:
        # Property comparison
        prop_diff = version_service.compare_versions(v1, v2)

        # File comparison
        file_diff = file_service.compare_version_files(v1, v2)

        return {"property_comparison": prop_diff, "file_comparison": file_diff}
    except (VersionError, VersionFileError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@version_router.get("/items/{item_id}/tree-full")
def get_version_tree_full(item_id: str, db: Session = Depends(get_db)):
    """
    Get version tree with file counts and thumbnails.
    """
    version_service = VersionService(db)

    # Get basic tree
    tree = version_service.get_version_tree(item_id)

    # Enrich with file info
    for node in tree:
        version = db.get(ItemVersion, node["id"])
        if version:
            node["file_count"] = version.file_count or 0
            node["thumbnail"] = version.thumbnail_data
            node["primary_file_id"] = version.primary_file_id

    return tree


# ===============================
# Sprint 4: Iteration Endpoints
# ===============================


class CreateIterationRequest(BaseModel):
    properties: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    source_type: str = "manual"


@version_router.post("/{version_id}/iterations")
def create_iteration(
    version_id: str,
    request: CreateIterationRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a new iteration within a version.
    Iterations are lightweight work-in-progress saves.
    """
    service = IterationService(db)
    try:
        iteration = service.create_iteration(
            version_id=version_id,
            user_id=user_id,
            properties=request.properties,
            description=request.description,
            source_type=request.source_type,
        )
        db.commit()
        return {
            "id": iteration.id,
            "version_id": iteration.version_id,
            "iteration_number": iteration.iteration_number,
            "iteration_label": iteration.iteration_label,
            "is_latest": iteration.is_latest,
            "source_type": iteration.source_type,
            "created_at": (
                iteration.created_at.isoformat() if iteration.created_at else None
            ),
        }
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@version_router.get("/{version_id}/iterations")
def get_iterations(version_id: str, db: Session = Depends(get_db)):
    """Get all iterations for a version."""
    service = IterationService(db)
    iterations = service.get_iterations(version_id)
    return [
        {
            "id": it.id,
            "iteration_number": it.iteration_number,
            "iteration_label": it.iteration_label,
            "is_latest": it.is_latest,
            "source_type": it.source_type,
            "description": it.description,
            "created_at": it.created_at.isoformat() if it.created_at else None,
        }
        for it in iterations
    ]


@version_router.get("/{version_id}/iterations/latest")
def get_latest_iteration(version_id: str, db: Session = Depends(get_db)):
    """Get the latest iteration for a version."""
    service = IterationService(db)
    iteration = service.get_latest_iteration(version_id)
    if not iteration:
        raise HTTPException(status_code=404, detail="No iterations found")
    return {
        "id": iteration.id,
        "iteration_number": iteration.iteration_number,
        "iteration_label": iteration.iteration_label,
        "is_latest": iteration.is_latest,
        "properties": iteration.properties,
        "description": iteration.description,
        "created_at": (
            iteration.created_at.isoformat() if iteration.created_at else None
        ),
    }


@version_router.post("/iterations/{iteration_id}/restore")
def restore_iteration(
    iteration_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Restore a previous iteration as the latest."""
    service = IterationService(db)
    try:
        iteration = service.restore_iteration(iteration_id, user_id)
        db.commit()
        return {
            "id": iteration.id,
            "iteration_number": iteration.iteration_number,
            "iteration_label": iteration.iteration_label,
            "is_latest": iteration.is_latest,
        }
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@version_router.delete("/iterations/{iteration_id}")
def delete_iteration(iteration_id: str, db: Session = Depends(get_db)):
    """Delete an iteration (not the latest one)."""
    service = IterationService(db)
    try:
        success = service.delete_iteration(iteration_id)
        if not success:
            raise HTTPException(status_code=404, detail="Iteration not found")
        db.commit()
        return {"status": "deleted"}
    except VersionError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ===============================
# Sprint 4: Revision Scheme Endpoints
# ===============================


class CreateRevisionSchemeRequest(BaseModel):
    name: str
    scheme_type: str = "letter"  # letter, number, hybrid
    initial_revision: str = "A"
    item_type_id: Optional[str] = None
    is_default: bool = False
    description: Optional[str] = None


@version_router.post("/schemes")
def create_revision_scheme(
    request: CreateRevisionSchemeRequest, db: Session = Depends(get_db)
):
    """Create a new revision numbering scheme."""
    service = RevisionSchemeService(db)
    scheme = service.create_scheme(
        name=request.name,
        scheme_type=request.scheme_type,
        initial_revision=request.initial_revision,
        item_type_id=request.item_type_id,
        is_default=request.is_default,
        description=request.description,
    )
    db.commit()
    return {
        "id": scheme.id,
        "name": scheme.name,
        "scheme_type": scheme.scheme_type,
        "initial_revision": scheme.initial_revision,
        "item_type_id": scheme.item_type_id,
        "is_default": scheme.is_default,
    }


@version_router.get("/schemes")
def list_revision_schemes(db: Session = Depends(get_db)):
    """List all revision schemes."""
    service = RevisionSchemeService(db)
    schemes = service.list_schemes()
    return [
        {
            "id": s.id,
            "name": s.name,
            "scheme_type": s.scheme_type,
            "initial_revision": s.initial_revision,
            "item_type_id": s.item_type_id,
            "is_default": s.is_default,
            "description": s.description,
        }
        for s in schemes
    ]


@version_router.get("/schemes/for-type/{item_type_id}")
def get_scheme_for_item_type(item_type_id: str, db: Session = Depends(get_db)):
    """Get the revision scheme for a specific ItemType."""
    service = RevisionSchemeService(db)
    scheme = service.get_scheme_for_item_type(item_type_id)
    if not scheme:
        # Return default
        return {"scheme_type": "letter", "initial_revision": "A", "is_default": True}
    return {
        "id": scheme.id,
        "name": scheme.name,
        "scheme_type": scheme.scheme_type,
        "initial_revision": scheme.initial_revision,
        "item_type_id": scheme.item_type_id,
        "is_default": scheme.is_default,
    }


# ===============================
# Sprint 4: Revision Calculation Utility
# ===============================


@version_router.get("/revision/next")
def calculate_next_revision(
    current: str, scheme: str = "letter", db: Session = Depends(get_db)
):
    """
    Calculate the next revision string.
    Useful for UI previews.
    """
    service = VersionService(db)
    next_rev = service._next_revision(current, scheme)
    return {"current": current, "next": next_rev, "scheme": scheme}


@version_router.get("/revision/parse")
def parse_revision(revision: str, db: Session = Depends(get_db)):
    """Parse a revision string into components."""
    service = VersionService(db)
    return service.parse_revision(revision)


@version_router.get("/revision/compare")
def compare_revisions(rev_a: str, rev_b: str, db: Session = Depends(get_db)):
    """
    Compare two revisions.
    Returns -1 if a < b, 0 if equal, 1 if a > b.
    """
    service = VersionService(db)
    result = service.compare_revisions(rev_a, rev_b)
    return {
        "rev_a": rev_a,
        "rev_b": rev_b,
        "comparison": result,
        "description": "a < b" if result < 0 else ("a > b" if result > 0 else "a == b"),
    }
