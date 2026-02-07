from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.meta_engine.services.release_validation import get_release_validation_directory


release_validation_router = APIRouter(
    prefix="/release-validation",
    tags=["Release Validation"],
)


@release_validation_router.get("/rulesets", response_model=Dict[str, Any])
def list_release_validation_rulesets(
    kind: Optional[str] = Query(None, description="Optional kind filter (e.g. routing_release)"),
    _user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        directory = get_release_validation_directory()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if kind:
        kinds = [k for k in (directory.get("kinds") or []) if k.get("kind") == kind]
        if not kinds:
            raise HTTPException(status_code=404, detail=f"Unknown kind: {kind}")
        return {"kinds": kinds}

    return directory

