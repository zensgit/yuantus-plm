"""B2: assembly release hard gate.

Release diagnostics for a Part item: a released parent must not reference
**unreleased direct ASSEMBLY children** (the WP1.2 CAD product structure). This is
orthogonal to ``mbom_release`` (manufacturing BOM) and is enforced as a HARD block
at ``LifecycleService.promote`` when an item enters ``Released`` (using the
``readiness`` ruleset, since the item itself is mid-transition there), and also
surfaced advisorily in ``release_readiness``.

Mirrors ``baseline_service.get_release_diagnostics`` (errors/warnings +
``ValidationIssue`` + ``get_release_ruleset``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from yuantus.meta_engine.lifecycle.models import LifecycleState
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.services.item_number_keys import get_item_number
from yuantus.meta_engine.services.release_validation import (
    ValidationIssue,
    get_release_ruleset,
)

# Fallback ONLY when a child has no resolvable LifecycleState row. Deliberately
# narrow: just the literal released marker. "approved" is an ECO/approval concept,
# NOT a Part release state (the seeded Part lifecycle is Draft/In Review/Released/
# Suspended/Obsolete) -- treating it as released would let an unreleased child pass
# the hard gate (fail-open). When in doubt, a hard gate must fail CLOSED.
_RELEASED_STATE_STRINGS = {"released"}
_ASSEMBLY = "ASSEMBLY"


class ItemReleaseService:
    def __init__(self, session: Session):
        self.session = session

    def _is_released(self, item: Item) -> bool:
        """Authoritative: the item's current LifecycleState.is_released. Falls back
        to the literal released state string ONLY when no LifecycleState row
        resolves (see ``_RELEASED_STATE_STRINGS`` -- narrow on purpose)."""
        if item.current_state:
            st = self.session.get(LifecycleState, item.current_state)
            if st is not None:
                return bool(st.is_released)
        return (item.state or "").strip().lower() in _RELEASED_STATE_STRINGS

    def _direct_assembly_children(
        self, item_id: str
    ) -> List[Tuple[Optional[Item], Item]]:
        """(child_item_or_None, edge) for EVERY current direct ASSEMBLY edge.
        A ``None`` child means a **dangling edge** -- ``related_id`` is NULL or
        points to a missing/removed Item. Such edges are returned (NOT skipped) so
        the caller can fail CLOSED on them; silently dropping them would let a
        parent with a broken BOM reference pass the hard gate (fail-open). Queries
        the edge Items directly (no ItemType resolve), so a DB without the ASSEMBLY
        type/edges simply yields no rows (vacuous pass), never an error."""
        edges = (
            self.session.query(Item)
            .filter(
                Item.source_id == item_id,
                Item.item_type_id == _ASSEMBLY,
                Item.is_current.is_(True),
            )
            .all()
        )
        return [(self.session.get(Item, edge.related_id), edge) for edge in edges]

    def assert_children_released(self, item_id: str) -> List[str]:
        """The promote hard gate: error messages for direct ASSEMBLY children that
        block release -- either a **dangling edge** (missing child) or an
        **unreleased** child (empty = gate passes). Focused -- it checks only
        children (the item itself is the one being promoted), so it does no
        item-existence / not_already_released check and does not re-fetch the
        promoting item."""
        messages: List[str] = []
        for child, edge in self._direct_assembly_children(item_id):
            if child is None:
                messages.append(
                    f"Assembly child is missing (dangling ASSEMBLY edge {edge.id} "
                    f"-> {edge.related_id})"
                )
            elif not self._is_released(child):
                number = get_item_number(child.properties or {}) or child.id
                messages.append(
                    f"Assembly child {number} is not released (state: {child.state})"
                )
        return messages

    def get_release_diagnostics(
        self, item_id: str, *, ruleset_id: str = "default"
    ) -> Dict[str, Any]:
        rules = get_release_ruleset("item_release", ruleset_id)
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []

        item = self.session.get(Item, item_id)
        if not item:
            errors.append(
                ValidationIssue(
                    code="item_not_found",
                    message=f"Item not found: {item_id}",
                    rule_id="item.exists",
                    details={"item_id": item_id},
                )
            )
            return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}

        for rule in rules:
            if rule == "item.exists":
                continue

            if rule == "item.not_already_released":
                if self._is_released(item):
                    errors.append(
                        ValidationIssue(
                            code="item_already_released",
                            message="Item is already released",
                            rule_id=rule,
                            details={"item_id": item_id},
                        )
                    )

            elif rule == "bom.children_all_released":
                for child, edge in self._direct_assembly_children(item_id):
                    if child is None:
                        # Dangling edge: related_id NULL or pointing at a missing
                        # Item. Fail CLOSED -- a broken BOM reference must block.
                        errors.append(
                            ValidationIssue(
                                code="child_missing",
                                message=(
                                    "Assembly child is missing (dangling ASSEMBLY "
                                    f"edge): {edge.related_id}"
                                ),
                                rule_id=rule,
                                details={
                                    "item_id": item_id,
                                    "child_id": edge.related_id,
                                    "relationship_id": edge.id,
                                },
                            )
                        )
                    elif not self._is_released(child):
                        child_number = get_item_number(child.properties or {})
                        errors.append(
                            ValidationIssue(
                                code="child_not_released",
                                message=(
                                    f"Assembly child {child_number or child.id} is not "
                                    f"released (state: {child.state})"
                                ),
                                rule_id=rule,
                                details={
                                    "item_id": item_id,
                                    "child_id": child.id,
                                    "child_number": child_number,
                                    "child_state": child.state,
                                    "relationship_id": edge.id,
                                },
                            )
                        )

        return {"ruleset_id": ruleset_id, "errors": errors, "warnings": warnings}
