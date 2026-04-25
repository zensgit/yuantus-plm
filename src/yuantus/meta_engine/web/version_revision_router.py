"""Version revision scheme and utility API endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.version.service import RevisionSchemeService, VersionService

version_revision_router = APIRouter(prefix="/versions", tags=["Versioning"])


class CreateRevisionSchemeRequest(BaseModel):
    name: str
    scheme_type: str = "letter"  # letter, number, hybrid
    initial_revision: str = "A"
    item_type_id: Optional[str] = None
    is_default: bool = False
    description: Optional[str] = None


@version_revision_router.post("/schemes")
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


@version_revision_router.get("/schemes")
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


@version_revision_router.get("/schemes/for-type/{item_type_id}")
def get_scheme_for_item_type(item_type_id: str, db: Session = Depends(get_db)):
    """Get the revision scheme for a specific ItemType."""
    service = RevisionSchemeService(db)
    scheme = service.get_scheme_for_item_type(item_type_id)
    if not scheme:
        return {"scheme_type": "letter", "initial_revision": "A", "is_default": True}
    return {
        "id": scheme.id,
        "name": scheme.name,
        "scheme_type": scheme.scheme_type,
        "initial_revision": scheme.initial_revision,
        "item_type_id": scheme.item_type_id,
        "is_default": scheme.is_default,
    }


@version_revision_router.get("/revision/next")
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


@version_revision_router.get("/revision/parse")
def parse_revision(revision: str, db: Session = Depends(get_db)):
    """Parse a revision string into components."""
    service = VersionService(db)
    return service.parse_revision(revision)


@version_revision_router.get("/revision/compare")
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
