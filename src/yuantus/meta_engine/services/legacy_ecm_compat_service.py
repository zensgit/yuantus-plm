"""
Legacy ECM Compatibility Service
================================
Maps old /ecm endpoint semantics to the canonical /eco service layer.

This module exists solely to support the deprecation period of the /ecm API.
No new business logic should be added here.  Once /ecm is fully retired,
delete this file and change_router.py together.

See: PR-0.5 audit (scripts/audit_ecm_legacy.py) for the full legacy surface.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from yuantus.meta_engine.models.eco import ECO, ECOState
from yuantus.meta_engine.services.eco_service import ECOService
from yuantus.meta_engine.services.impact_analysis_service import ImpactAnalysisService


class LegacyEcmCompatService:
    """Thin adapter from old /ecm shapes to canonical ECOService calls."""

    def __init__(self, session: Session):
        self.session = session
        self.eco_service = ECOService(session)

    # ------------------------------------------------------------------
    # GET /ecm/items/{item_id}/impact  →  impact analysis (read-only)
    # ------------------------------------------------------------------

    def get_impact_analysis(self, item_id: str) -> Dict[str, Any]:
        """Return old-format impact analysis for an item.

        Old shape: { where_used: [...], pending_changes: [...] }
        We map to the new ImpactAnalysisService for where_used,
        and query open ECOs for pending_changes.
        """
        impact_service = ImpactAnalysisService(self.session)

        # where_used via new service
        try:
            where_used = impact_service.where_used(item_id)
        except Exception:
            where_used = []

        # pending_changes: open ECOs referencing this product
        pending_ecos: List[Dict[str, Any]] = []
        open_states = {
            ECOState.DRAFT.value,
            ECOState.PROGRESS.value,
            ECOState.APPROVED.value,
            ECOState.SUSPENDED.value,
            ECOState.CONFLICT.value,
        }
        ecos = (
            self.session.query(ECO)
            .filter(ECO.product_id == item_id, ECO.state.in_(open_states))
            .all()
        )
        for eco in ecos:
            pending_ecos.append(eco.to_dict())

        return {"where_used": where_used, "pending_changes": pending_ecos}

    # ------------------------------------------------------------------
    # POST /ecm/eco/{eco_id}/affected-items  →  bind_product (write)
    # ------------------------------------------------------------------

    def add_affected_item_compat(
        self, eco_id: str, target_item_id: str, action: str, user_id: int
    ) -> Dict[str, Any]:
        """Map old 'add affected item' to new bind_product.

        Only action="Change" is supported.  Other actions (Release, Revise,
        New Generation) are rejected with a clear error directing callers
        to the canonical /eco flow.
        """
        if action != "Change":
            raise ValueError(
                f"Action '{action}' is not supported via the legacy /ecm endpoint. "
                f"Use the canonical /eco API for Release, Revise, or New Generation workflows."
            )

        eco = self.eco_service.bind_product(
            eco_id, target_item_id, user_id, create_target_revision=False
        )
        return eco.to_dict()

    # ------------------------------------------------------------------
    # POST /ecm/eco/{eco_id}/execute  →  diagnostics + apply (write)
    # ------------------------------------------------------------------

    def execute_eco_compat(self, eco_id: str, user_id: int) -> Dict[str, Any]:
        """Map old 'execute ECO' to new diagnostics → apply flow.

        Unlike the old ChangeService.execute_eco() which directly iterated
        affected items and performed Release/Revise/New Generation, this
        routes through the canonical ECO apply pipeline which requires the
        ECO to be in APPROVED state.
        """
        eco = self.eco_service.get_eco(eco_id)
        if not eco:
            raise ValueError(f"ECO with ID '{eco_id}' not found.")

        if eco.state != ECOState.APPROVED.value:
            raise ValueError(
                f"Cannot execute ECO in '{eco.state}' state. "
                f"The ECO must be in 'approved' state before execution. "
                f"Use the canonical /eco API to move through the approval workflow."
            )

        # Run diagnostics first
        diagnostics = self.eco_service.get_apply_diagnostics(eco_id, user_id)
        errors = diagnostics.get("errors", [])
        if errors:
            error_msgs = "; ".join(
                e.get("message", str(e)) if isinstance(e, dict) else str(e)
                for e in errors
            )
            raise ValueError(
                f"ECO apply blocked by diagnostics: {error_msgs}"
            )

        self.eco_service.action_apply(eco_id, user_id)
        return {"status": "success", "message": f"ECO {eco_id} applied via canonical pipeline"}
