"""
Spare Service
Manages spare parts: designating which Parts are spare parts of a
product/assembly, and exposing an exploded spare-parts view down the assembly.

Data Model:
- ItemType: "Part Spare" (is_relationship=True)
- Source ID: The ID of the product/assembly Part.
- Related ID: The ID of the spare-part Part.

Directional (assembly -> spare), mirroring EquivalentService in shape but NOT
symmetric (equivalents are peer-to-peer; spares hang off the owning assembly).
The exploded view reuses BOMService.get_bom_structure (read-only) to walk the
assembly and collect each part's direct spares, rather than reinventing BOM
traversal.

OdooPLM gap parity (G5), modeled entirely on Yuantus's own item-relationship
precedent (substitute/equivalent). No purchase / inventory / pricing (ERP-side,
out of scope), no bespoke table, no migration — the "Part Spare" ItemType and
the spare relationship-Items live in the existing item/relationship tables.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.security.rbac.permissions import (
    PermissionManager as MetaPermissionService,
)


SPARE_ITEM_TYPE = "Part Spare"


class SpareService:
    def __init__(
        self, session: Session, user_id: str = "1", roles: Optional[List[str]] = None
    ):
        self.session = session
        self.user_id = user_id
        self.roles = roles or []
        self.permission_service = MetaPermissionService()

    def ensure_spare_item_type(self) -> None:
        """Ensure the 'Part Spare' ItemType exists.

        §9.6 hardening: unlike the substitute/equivalent precedent (plain
        check-then-insert with no guard), this tolerates the concurrent
        first-call race — two callers both observing the type absent and both
        inserting the same primary key. The losing commit raises IntegrityError,
        which we swallow after rolling back and re-confirming the row now exists
        (created by the winner). Spare therefore does not import the latent race
        the precedent carries.
        """
        existing = self.session.query(ItemType).filter_by(id=SPARE_ITEM_TYPE).first()
        if existing:
            return
        new_type = ItemType(
            id=SPARE_ITEM_TYPE,
            label="Part Spare",
            description="Spare part of a product/assembly",
            is_relationship=True,
            is_versionable=False,
        )
        self.session.add(new_type)
        try:
            self.session.commit()
        except IntegrityError:
            # A concurrent caller created it first: roll back and re-confirm.
            self.session.rollback()
            existing = (
                self.session.query(ItemType).filter_by(id=SPARE_ITEM_TYPE).first()
            )
            if existing is None:
                raise

    def add_spare(
        self,
        item_id: str,
        spare_item_id: str,
        properties: Optional[Dict[str, Any]] = None,
        user_id: int = 1,
    ) -> Item:
        """Designate ``spare_item_id`` as a spare part of ``item_id`` (directional).

        Conventional ``properties`` keys (free-form, not enforced): ``quantity``
        (consumers treat absent as 1), ``position``/``ref``, ``notes``.
        """
        self.permission_service.check_permission(user_id, "create", SPARE_ITEM_TYPE)
        self.ensure_spare_item_type()

        if item_id == spare_item_id:
            raise ValueError("Item cannot be a spare of itself")

        item = self.session.get(Item, item_id)
        if not item or item.item_type_id != "Part":
            raise ValueError(f"Invalid Part ID: {item_id}")

        spare_item = self.session.get(Item, spare_item_id)
        if not spare_item or spare_item.item_type_id != "Part":
            raise ValueError(f"Invalid Part ID: {spare_item_id}")

        existing = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == SPARE_ITEM_TYPE,
                Item.is_current.is_(True),
                Item.source_id == item_id,
                Item.related_id == spare_item_id,
            )
            .first()
        )
        if existing:
            raise ValueError("Spare relationship already exists")

        rel = Item(
            id=str(uuid.uuid4()),
            item_type_id=SPARE_ITEM_TYPE,
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            source_id=item_id,
            related_id=spare_item_id,
            properties=properties or {},
            created_by_id=user_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(rel)
        self.session.commit()
        return rel

    def list_spares(self, item_id: str) -> List[Dict[str, Any]]:
        """List the direct spare parts designated for ``item_id`` (source side)."""
        rels = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == SPARE_ITEM_TYPE,
                Item.is_current.is_(True),
                Item.source_id == item_id,
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for rel in rels:
            spare_item = (
                self.session.get(Item, rel.related_id) if rel.related_id else None
            )
            rel_dict = rel.to_dict()
            rel_dict["properties"] = rel.properties or {}
            result.append(
                {
                    "id": rel.id,
                    "spare_item_id": rel.related_id,
                    "spare_part": spare_item.to_dict() if spare_item else None,
                    "relationship": rel_dict,
                }
            )
        return result

    def remove_spare(self, rel_id: str, user_id: int) -> None:
        """Remove a spare relationship by ID."""
        self.permission_service.check_permission(
            user_id, "delete", SPARE_ITEM_TYPE, resource_id=rel_id
        )

        rel = self.session.get(Item, rel_id)
        if not rel or rel.item_type_id != SPARE_ITEM_TYPE:
            raise ValueError(f"Spare relationship {rel_id} not found")

        self.session.delete(rel)
        self.session.commit()

    def explode_spares(self, item_id: str, levels: int = 10) -> List[Dict[str, Any]]:
        """Exploded spare-parts view: the spares of ``item_id`` plus the spares
        of every Part reachable down its BOM (read-only).

        Reuses ``BOMService.get_bom_structure`` (``relationship_types=["Part BOM"]``)
        for the assembly traversal — preserving its is_current / effectivity
        semantics — then collects each unique part's direct spares. Imported
        lazily (the codebase's own service-to-service pattern) to avoid an import
        cycle. Returns one group per part that has at least one spare, in
        document order (root first).
        """
        from yuantus.meta_engine.services.bom_service import BOMService

        bom = BOMService(self.session)
        tree = bom.get_bom_structure(
            item_id, levels=levels, relationship_types=["Part BOM"]
        )

        ordered_ids = []
        seen = set()

        def _walk(node: Dict[str, Any]) -> None:
            node_id = node.get("id")
            if node_id and node_id not in seen:
                seen.add(node_id)
                ordered_ids.append(node_id)
            for entry in node.get("children") or []:
                child = entry.get("child")
                if isinstance(child, dict):
                    _walk(child)

        _walk(tree)

        result: List[Dict[str, Any]] = []
        for pid in ordered_ids:
            spares = self.list_spares(pid)
            if spares:
                result.append(
                    {"item_id": pid, "spares": spares, "count": len(spares)}
                )
        return result
