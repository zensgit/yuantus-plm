"""
ECO change analysis router slice.

R5 of the ECO router decomposition owns BOM/routing change read surfaces,
change computation, and rebase conflict diagnostics. Lifecycle and CRUD
actions remain in the legacy ECO router.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from yuantus.database import get_db
from yuantus.meta_engine.services.eco_service import ECOService

eco_change_analysis_router = APIRouter(prefix="/eco", tags=["ECO"])


@eco_change_analysis_router.get(
    "/{eco_id}/routing-changes", response_model=List[Dict[str, Any]]
)
async def get_routing_changes(eco_id: str, db: Session = Depends(get_db)):
    """Get all routing changes for an ECO."""
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    changes = service.get_routing_changes(eco_id)
    return [change.to_dict() for change in changes]


@eco_change_analysis_router.post(
    "/{eco_id}/compute-routing-changes", response_model=List[Dict[str, Any]]
)
async def compute_routing_changes(
    eco_id: str,
    compare_mode: Optional[str] = Query(
        None,
        description="Optional compare mode for routing change computation",
    ),
    db: Session = Depends(get_db),
):
    """Compute routing differences between the ECO source and target versions."""
    service = ECOService(db)
    try:
        changes = service.compute_routing_changes(eco_id, compare_mode=compare_mode)
        db.commit()
        return changes
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@eco_change_analysis_router.get(
    "/{eco_id}/changes", response_model=List[Dict[str, Any]]
)
async def get_bom_changes(eco_id: str, db: Session = Depends(get_db)):
    """Get all BOM changes for an ECO."""
    service = ECOService(db)
    eco = service.get_eco(eco_id)
    if not eco:
        raise HTTPException(status_code=404, detail="ECO not found")

    changes = service.get_bom_changes(eco_id)
    return [c.to_dict() for c in changes]


@eco_change_analysis_router.post(
    "/{eco_id}/compute-changes", response_model=List[Dict[str, Any]]
)
async def compute_bom_changes(
    eco_id: str,
    compare_mode: Optional[str] = Query(
        None,
        description=(
            "Optional compare mode: only_product, summarized, by_item, num_qty, "
            "by_position, by_reference, by_find_refdes"
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Compute BOM differences between source and target versions.
    Creates/updates ECOBOMChange records.
    """
    service = ECOService(db)
    try:
        changes = service.compute_bom_changes(eco_id, compare_mode=compare_mode)
        db.commit()
        return [c.to_dict() for c in changes]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@eco_change_analysis_router.get(
    "/{eco_id}/conflicts", response_model=List[Dict[str, Any]]
)
async def detect_conflicts(eco_id: str, db: Session = Depends(get_db)):
    """
    Detect rebase conflicts for an ECO.
    Compares Base (source) vs Mine (target) vs Theirs (current product version).
    """
    service = ECOService(db)
    try:
        conflicts = service.detect_rebase_conflicts(eco_id)
        return conflicts
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
