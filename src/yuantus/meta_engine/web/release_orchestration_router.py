from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from yuantus.api.dependencies.auth import CurrentUser, get_current_user
from yuantus.config import get_settings
from yuantus.database import get_db
from yuantus.meta_engine.manufacturing.mbom_service import MBOMService
from yuantus.meta_engine.manufacturing.routing_service import RoutingService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.baseline_service import BaselineService
from yuantus.meta_engine.services.release_validation import get_release_ruleset
from yuantus.meta_engine.services.release_readiness_service import ReleaseReadinessService
from yuantus.meta_engine.web.release_diagnostics_models import (
    ReleaseDiagnosticsResponse,
    issue_to_response,
)
from yuantus.meta_engine.web.release_readiness_router import (
    ReleaseReadinessResponse,
    _build_response,
)


release_orchestration_router = APIRouter(
    prefix="/release-orchestration",
    tags=["Release Orchestration"],
)

_FAILPOINT_HEADER = "x-yuantus-failpoint"


def _ensure_admin(user: CurrentUser) -> None:
    roles = {str(r).strip().lower() for r in (user.roles or []) if str(r).strip()}
    if bool(getattr(user, "is_superuser", False)):
        return
    if "admin" in roles or "superuser" in roles:
        return
    raise HTTPException(status_code=403, detail="Admin permission required")


def _diag_response(
    *,
    ok: bool,
    resource_type: str,
    resource_id: str,
    ruleset_id: str,
    errors: List[Any],
    warnings: List[Any],
) -> ReleaseDiagnosticsResponse:
    err = [issue_to_response(issue) for issue in (errors or [])]
    warn = [issue_to_response(issue) for issue in (warnings or [])]
    return ReleaseDiagnosticsResponse(
        ok=bool(ok),
        resource_type=str(resource_type or "unknown"),
        resource_id=str(resource_id or ""),
        ruleset_id=str(ruleset_id or ""),
        errors=err,
        warnings=warn,
    )


def _build_readiness(
    *,
    item_id: str,
    ruleset_id: str,
    mbom_limit: int,
    routing_limit: int,
    baseline_limit: int,
    db: Session,
) -> ReleaseReadinessResponse:
    svc = ReleaseReadinessService(db)
    payload = svc.get_item_release_readiness(
        item_id=item_id,
        ruleset_id=ruleset_id,
        mbom_limit=mbom_limit,
        routing_limit=routing_limit,
        baseline_limit=baseline_limit,
    )
    return _build_response(payload=payload, ruleset_id=ruleset_id)


class OrchestrationStep(BaseModel):
    kind: str
    resource_type: str
    resource_id: str
    state: Optional[str] = None
    action: str
    diagnostics: ReleaseDiagnosticsResponse


class ReleaseOrchestrationPlanResponse(BaseModel):
    item_id: str
    generated_at: datetime
    ruleset_id: str
    readiness: ReleaseReadinessResponse
    steps: List[OrchestrationStep] = Field(default_factory=list)


class ReleaseOrchestrationExecuteRequest(BaseModel):
    ruleset_id: str = Field(default="default", max_length=100)
    include_routings: bool = True
    include_mboms: bool = True
    include_baselines: bool = False
    routing_limit: int = Field(default=20, ge=0, le=200)
    mbom_limit: int = Field(default=20, ge=0, le=200)
    baseline_limit: int = Field(default=20, ge=0, le=200)
    continue_on_error: bool = False
    rollback_on_failure: bool = False
    dry_run: bool = False
    baseline_force: bool = False


class ReleaseOrchestrationStepResult(BaseModel):
    kind: str
    resource_type: str
    resource_id: str
    status: str
    state_before: Optional[str] = None
    state_after: Optional[str] = None
    diagnostics: ReleaseDiagnosticsResponse
    message: Optional[str] = None


class ReleaseOrchestrationExecuteResponse(BaseModel):
    item_id: str
    generated_at: datetime
    ruleset_id: str
    dry_run: bool
    results: List[ReleaseOrchestrationStepResult] = Field(default_factory=list)
    post_readiness: Optional[ReleaseReadinessResponse] = None


def _plan_steps(readiness: ReleaseReadinessResponse) -> List[OrchestrationStep]:
    steps: List[OrchestrationStep] = []
    esign_manifest = readiness.esign_manifest
    esign_incomplete = (
        isinstance(esign_manifest, dict)
        and ("is_complete" in esign_manifest)
        and (not bool(esign_manifest.get("is_complete")))
    )

    for res in readiness.resources or []:
        kind = res.kind
        diag = res.diagnostics
        state = res.state
        state_l = (state or "").strip().lower()

        if state_l == "released":
            action = "skip_already_released"
        elif not diag.ok:
            action = "skip_errors"
        else:
            action = "release"

        if kind == "baseline_release" and action == "release" and esign_incomplete:
            action = "requires_esign"

        steps.append(
            OrchestrationStep(
                kind=kind,
                resource_type=diag.resource_type,
                resource_id=diag.resource_id,
                state=state,
                action=action,
                diagnostics=diag,
            )
        )

    # Execution order: routing -> mbom -> baseline (baseline independent; mbom may depend on released routing).
    order = {"routing_release": 10, "mbom_release": 20, "baseline_release": 30}
    steps.sort(key=lambda s: (order.get(s.kind, 100), str(s.resource_id)))
    return steps


def _maybe_inject_failpoint(*, request: Request, kind: str, resource_type: str, resource_id: str) -> None:
    """
    Test-only failure injection for E2E coverage of rollback paths.

    Enabled only when `YUANTUS_TEST_FAILPOINTS_ENABLED=true` and a matching
    `x-yuantus-failpoint` header is present.
    """
    settings = get_settings()
    if not bool(getattr(settings, "TEST_FAILPOINTS_ENABLED", False)):
        return
    fp = (request.headers.get(_FAILPOINT_HEADER) or "").strip()
    if not fp:
        return

    candidates = {
        f"{kind}:{resource_id}",
        f"{resource_type}:{resource_id}",
        f"release-orchestration:{kind}:{resource_id}",
        f"release-orchestration:{resource_type}:{resource_id}",
    }
    if fp in candidates:
        raise ValueError(f"Injected failure via {_FAILPOINT_HEADER}")


@release_orchestration_router.get(
    "/items/{item_id}/plan",
    response_model=ReleaseOrchestrationPlanResponse,
)
def get_release_plan(
    item_id: str,
    ruleset_id: str = Query("default"),
    routing_limit: int = Query(20, ge=0, le=200),
    mbom_limit: int = Query(20, ge=0, le=200),
    baseline_limit: int = Query(20, ge=0, le=200),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReleaseOrchestrationPlanResponse:
    _ensure_admin(user)

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    try:
        readiness = _build_readiness(
            item_id=item_id,
            ruleset_id=ruleset_id,
            mbom_limit=mbom_limit,
            routing_limit=routing_limit,
            baseline_limit=baseline_limit,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    steps = _plan_steps(readiness)
    return ReleaseOrchestrationPlanResponse(
        item_id=item_id,
        generated_at=datetime.utcnow(),
        ruleset_id=ruleset_id,
        readiness=readiness,
        steps=steps,
    )


@release_orchestration_router.post(
    "/items/{item_id}/execute",
    response_model=ReleaseOrchestrationExecuteResponse,
)
def execute_release_plan(
    item_id: str,
    req: ReleaseOrchestrationExecuteRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReleaseOrchestrationExecuteResponse:
    _ensure_admin(user)

    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")

    ruleset_id = (req.ruleset_id or "default").strip() or "default"

    try:
        if req.include_routings:
            get_release_ruleset("routing_release", ruleset_id)
        if req.include_mboms:
            get_release_ruleset("mbom_release", ruleset_id)
        if req.include_baselines:
            get_release_ruleset("baseline_release", ruleset_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if bool(req.rollback_on_failure) and bool(req.continue_on_error):
        raise HTTPException(
            status_code=400,
            detail="rollback_on_failure requires continue_on_error=false",
        )

    # Select resources using the same listing logic as release readiness, so plan/execute stay aligned.
    readiness_svc = ReleaseReadinessService(db)
    mboms = readiness_svc.list_mboms(item_id=item_id, limit=req.mbom_limit)
    mbom_ids = [m.id for m in mboms]
    routings = readiness_svc.list_routings(item_id=item_id, mbom_ids=mbom_ids, limit=req.routing_limit)
    baselines = readiness_svc.list_baselines(item_id=item_id, limit=req.baseline_limit)

    # Keep execution ordering stable and aligned with plan sorting (resource_id asc).
    mboms.sort(key=lambda m: str(getattr(m, "id", "")))
    routings.sort(key=lambda r: str(getattr(r, "id", "")))
    baselines.sort(key=lambda b: str(getattr(b, "id", "")))

    routing_svc = RoutingService(db)
    mbom_svc = MBOMService(db)
    baseline_svc = BaselineService(db)

    results: List[ReleaseOrchestrationStepResult] = []
    released_routing_ids: List[str] = []
    released_mbom_ids: List[str] = []

    def _record(
        *,
        kind: str,
        resource_type: str,
        resource_id: str,
        status: str,
        state_before: Optional[str],
        state_after: Optional[str],
        diagnostics: Dict[str, Any],
        message: Optional[str] = None,
    ) -> None:
        diag = _diag_response(
            ok=(len(diagnostics.get("errors") or []) == 0),
            resource_type=resource_type,
            resource_id=resource_id,
            ruleset_id=str(diagnostics.get("ruleset_id") or ruleset_id),
            errors=diagnostics.get("errors") or [],
            warnings=diagnostics.get("warnings") or [],
        )
        results.append(
            ReleaseOrchestrationStepResult(
                kind=kind,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                state_before=state_before,
                state_after=state_after,
                diagnostics=diag,
                message=message,
            )
        )

    def _should_stop_on_failure() -> bool:
        return not bool(req.continue_on_error)

    abort = False

    esign_status: Any = None
    esign_incomplete = False
    missing_required_meanings: List[str] = []
    if req.include_baselines:
        try:
            esign_status = readiness_svc.get_esign_manifest_status(item_id=item_id)
        except Exception:
            esign_status = None
        if (
            isinstance(esign_status, dict)
            and ("is_complete" in esign_status)
            and (not bool(esign_status.get("is_complete")))
        ):
            esign_incomplete = True
            try:
                reqs = esign_status.get("requirements") or []
                for entry in reqs:
                    if not isinstance(entry, dict):
                        continue
                    if not bool(entry.get("required")):
                        continue
                    if bool(entry.get("signed")):
                        continue
                    meaning = (entry.get("meaning") or "").strip()
                    if meaning:
                        missing_required_meanings.append(meaning)
            except Exception:
                missing_required_meanings = []

    # 1) Routings (may unblock MBOM release rules that require released routing).
    if req.include_routings and not abort:
        for routing in routings:
            rid = str(routing.id)
            state_before = getattr(routing, "state", None)
            state_l = (state_before or "").strip().lower()
            diagnostics = routing_svc.get_release_diagnostics(rid, ruleset_id=ruleset_id)

            if state_l == "released":
                _record(
                    kind="routing_release",
                    resource_type="routing",
                    resource_id=rid,
                    status="skipped_already_released",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            if diagnostics.get("errors"):
                _record(
                    kind="routing_release",
                    resource_type="routing",
                    resource_id=rid,
                    status="skipped_errors",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            if req.dry_run:
                _record(
                    kind="routing_release",
                    resource_type="routing",
                    resource_id=rid,
                    status="planned",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            try:
                _maybe_inject_failpoint(
                    request=request,
                    kind="routing_release",
                    resource_type="routing",
                    resource_id=rid,
                )
                updated = routing_svc.release_routing(rid, ruleset_id=ruleset_id)
                db.commit()
                released_routing_ids.append(rid)
                _record(
                    kind="routing_release",
                    resource_type="routing",
                    resource_id=rid,
                    status="executed",
                    state_before=state_before,
                    state_after=getattr(updated, "state", None),
                    diagnostics=diagnostics,
                )
            except ValueError as exc:
                db.rollback()
                _record(
                    kind="routing_release",
                    resource_type="routing",
                    resource_id=rid,
                    status="failed",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                    message=str(exc),
                )
                if _should_stop_on_failure():
                    abort = True
                    break

    # 2) MBOMs
    if req.include_mboms and not abort:
        for mbom in mboms:
            mid = str(mbom.id)
            state_before = getattr(mbom, "state", None)
            state_l = (state_before or "").strip().lower()
            diagnostics = mbom_svc.get_release_diagnostics(mid, ruleset_id=ruleset_id)

            if state_l == "released":
                _record(
                    kind="mbom_release",
                    resource_type="mbom",
                    resource_id=mid,
                    status="skipped_already_released",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            if diagnostics.get("errors"):
                _record(
                    kind="mbom_release",
                    resource_type="mbom",
                    resource_id=mid,
                    status="skipped_errors",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            if req.dry_run:
                _record(
                    kind="mbom_release",
                    resource_type="mbom",
                    resource_id=mid,
                    status="planned",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            try:
                _maybe_inject_failpoint(
                    request=request,
                    kind="mbom_release",
                    resource_type="mbom",
                    resource_id=mid,
                )
                updated = mbom_svc.release_mbom(mid, ruleset_id=ruleset_id)
                db.commit()
                released_mbom_ids.append(mid)
                _record(
                    kind="mbom_release",
                    resource_type="mbom",
                    resource_id=mid,
                    status="executed",
                    state_before=state_before,
                    state_after=getattr(updated, "state", None),
                    diagnostics=diagnostics,
                )
            except ValueError as exc:
                db.rollback()
                _record(
                    kind="mbom_release",
                    resource_type="mbom",
                    resource_id=mid,
                    status="failed",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                    message=str(exc),
                )
                if _should_stop_on_failure():
                    abort = True
                    break

    # 3) Baselines (optional)
    if req.include_baselines and not abort:
        for baseline in baselines:
            bid = str(baseline.id)
            state_before = getattr(baseline, "state", None)
            state_l = (state_before or "").strip().lower()
            diagnostics = baseline_svc.get_release_diagnostics(bid, ruleset_id=ruleset_id)

            if state_l == "released":
                _record(
                    kind="baseline_release",
                    resource_type="baseline",
                    resource_id=bid,
                    status="skipped_already_released",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            if diagnostics.get("errors") and not bool(req.baseline_force):
                _record(
                    kind="baseline_release",
                    resource_type="baseline",
                    resource_id=bid,
                    status="skipped_errors",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            if esign_incomplete:
                message = "Electronic signature manifest incomplete"
                if missing_required_meanings:
                    shown = missing_required_meanings[:10]
                    suffix = "" if len(missing_required_meanings) <= 10 else ", ..."
                    message = f"{message}; missing required meanings: {', '.join(shown)}{suffix}"
                _record(
                    kind="baseline_release",
                    resource_type="baseline",
                    resource_id=bid,
                    status="blocked_esign_incomplete",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                    message=message,
                )
                if _should_stop_on_failure():
                    abort = True
                    break
                continue

            if req.dry_run:
                _record(
                    kind="baseline_release",
                    resource_type="baseline",
                    resource_id=bid,
                    status="planned",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                )
                continue

            try:
                _maybe_inject_failpoint(
                    request=request,
                    kind="baseline_release",
                    resource_type="baseline",
                    resource_id=bid,
                )
                updated = baseline_svc.release_baseline(
                    bid,
                    user_id=int(user.id),
                    force=bool(req.baseline_force),
                )
                _record(
                    kind="baseline_release",
                    resource_type="baseline",
                    resource_id=bid,
                    status="executed",
                    state_before=state_before,
                    state_after=getattr(updated, "state", None),
                    diagnostics=diagnostics,
                )
            except ValueError as exc:
                db.rollback()
                _record(
                    kind="baseline_release",
                    resource_type="baseline",
                    resource_id=bid,
                    status="failed",
                    state_before=state_before,
                    state_after=state_before,
                    diagnostics=diagnostics,
                    message=str(exc),
                )
                if _should_stop_on_failure():
                    abort = True
                    break

    # Best-effort rollback to "draft" for any resources released earlier in this run.
    if abort and bool(req.rollback_on_failure) and not bool(req.dry_run):
        empty_diag = {"ruleset_id": ruleset_id, "errors": [], "warnings": []}

        # Reopen MBOMs first (they may depend on routings).
        for mid in reversed(released_mbom_ids):
            try:
                before = "released"
                reopened = mbom_svc.reopen_mbom(mid)
                db.commit()
                _record(
                    kind="mbom_reopen",
                    resource_type="mbom",
                    resource_id=mid,
                    status="rolled_back",
                    state_before=before,
                    state_after=getattr(reopened, "state", None),
                    diagnostics=empty_diag,
                )
            except Exception as exc:
                db.rollback()
                _record(
                    kind="mbom_reopen",
                    resource_type="mbom",
                    resource_id=mid,
                    status="rollback_failed",
                    state_before="released",
                    state_after="released",
                    diagnostics=empty_diag,
                    message=str(exc),
                )

        for rid in reversed(released_routing_ids):
            try:
                before = "released"
                reopened = routing_svc.reopen_routing(rid)
                db.commit()
                _record(
                    kind="routing_reopen",
                    resource_type="routing",
                    resource_id=rid,
                    status="rolled_back",
                    state_before=before,
                    state_after=getattr(reopened, "state", None),
                    diagnostics=empty_diag,
                )
            except Exception as exc:
                db.rollback()
                _record(
                    kind="routing_reopen",
                    resource_type="routing",
                    resource_id=rid,
                    status="rollback_failed",
                    state_before="released",
                    state_after="released",
                    diagnostics=empty_diag,
                    message=str(exc),
                )

    post_readiness: Optional[ReleaseReadinessResponse] = None
    try:
        post_readiness = _build_readiness(
            item_id=item_id,
            ruleset_id=ruleset_id,
            mbom_limit=req.mbom_limit,
            routing_limit=req.routing_limit,
            baseline_limit=req.baseline_limit,
            db=db,
        )
    except Exception:
        post_readiness = None

    return ReleaseOrchestrationExecuteResponse(
        item_id=item_id,
        generated_at=datetime.utcnow(),
        ruleset_id=ruleset_id,
        dry_run=bool(req.dry_run),
        results=results,
        post_readiness=post_readiness,
    )
