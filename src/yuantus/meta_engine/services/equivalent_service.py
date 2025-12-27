"""
Equivalent Service
Manages equivalent parts (peer-to-peer relationships between Parts).

Data Model:
- ItemType: "Part Equivalent"
- Source ID: The ID of the primary Part.
- Related ID: The ID of the equivalent Part.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.security.rbac.permissions import (
    PermissionManager as MetaPermissionService,
)


class EquivalentService:
    def __init__(
        self, session: Session, user_id: str = "1", roles: Optional[List[str]] = None
    ):
        self.session = session
        self.user_id = user_id
        self.roles = roles or []
        self.permission_service = MetaPermissionService()

    def ensure_equivalent_item_type(self) -> None:
        """Ensures 'Part Equivalent' ItemType exists."""
        type_id = "Part Equivalent"
        existing = self.session.query(ItemType).filter_by(id=type_id).first()
        if existing:
            return
        new_type = ItemType(
            id=type_id,
            label="Part Equivalent",
            description="Equivalent part relationship",
            is_relationship=True,
            is_versionable=False,
        )
        self.session.add(new_type)
        self.session.commit()

    def add_equivalent(
        self,
        item_id: str,
        equivalent_item_id: str,
        properties: Optional[Dict[str, Any]] = None,
        user_id: int = 1,
    ) -> Item:
        """
        Add an equivalent part relationship.
        """
        self.permission_service.check_permission(
            user_id, "create", "Part Equivalent"
        )
        self.ensure_equivalent_item_type()

        if item_id == equivalent_item_id:
            raise ValueError("Item cannot be equivalent to itself")

        item = self.session.get(Item, item_id)
        if not item or item.item_type_id != "Part":
            raise ValueError(f"Invalid Part ID: {item_id}")

        eq_item = self.session.get(Item, equivalent_item_id)
        if not eq_item or eq_item.item_type_id != "Part":
            raise ValueError(f"Invalid Part ID: {equivalent_item_id}")

        existing = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == "Part Equivalent",
                Item.is_current.is_(True),
                or_(
                    and_(
                        Item.source_id == item_id,
                        Item.related_id == equivalent_item_id,
                    ),
                    and_(
                        Item.source_id == equivalent_item_id,
                        Item.related_id == item_id,
                    ),
                ),
            )
            .first()
        )
        if existing:
            raise ValueError("Equivalent relationship already exists")

        rel = Item(
            id=str(uuid.uuid4()),
            item_type_id="Part Equivalent",
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            source_id=item_id,
            related_id=equivalent_item_id,
            properties=properties or {},
            created_by_id=user_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(rel)
        self.session.commit()
        return rel

    def list_equivalents(self, item_id: str) -> List[Dict[str, Any]]:
        """
        Get all equivalents for a specific Part.
        """
        rels = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == "Part Equivalent",
                Item.is_current.is_(True),
                or_(Item.source_id == item_id, Item.related_id == item_id),
            )
            .all()
        )

        result: List[Dict[str, Any]] = []
        for rel in rels:
            other_id = rel.related_id if rel.source_id == item_id else rel.source_id
            other_item = self.session.get(Item, other_id) if other_id else None
            rel_dict = rel.to_dict()
            rel_dict["properties"] = rel.properties or {}
            result.append(
                {
                    "id": rel.id,
                    "equivalent_item_id": other_id,
                    "equivalent_part": other_item.to_dict() if other_item else None,
                    "relationship": rel_dict,
                }
            )
        return result

    def remove_equivalent(self, rel_id: str, user_id: int) -> None:
        """
        Remove an equivalent relationship by ID.
        """
        self.permission_service.check_permission(
            user_id, "delete", "Part Equivalent", resource_id=rel_id
        )

        rel = self.session.get(Item, rel_id)
        if not rel or rel.item_type_id != "Part Equivalent":
            raise ValueError(f"Equivalent relationship {rel_id} not found")

        self.session.delete(rel)
        self.session.commit()
