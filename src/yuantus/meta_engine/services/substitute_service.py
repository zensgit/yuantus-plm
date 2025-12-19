"""
Substitute Service
Manages BOM Substitutes (Alternative parts for specific BOM lines).

Data Model:
- ItemType: "Part BOM Substitute"
- Source ID: The ID of the "Part BOM" Relationship Item.
- Related ID: The ID of the Substitute Part Item.
"""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.engine import AMLEngine
from yuantus.security.rbac.permissions import (
    PermissionManager as MetaPermissionService,
)


class SubstituteService:
    def __init__(
        self, session: Session, user_id: str = "1", roles: Optional[List[str]] = None
    ):
        self.session = session
        self.user_id = user_id
        self.roles = roles or []
        self.aml_engine = AMLEngine(session, identity_id=user_id, roles=self.roles)
        self.permission_service = MetaPermissionService()

    def ensure_substitute_item_type(self):
        """Ensures 'Part BOM Substitute' ItemType exists."""
        type_id = "Part BOM Substitute"
        existing = self.session.query(ItemType).filter_by(id=type_id).first()
        if not existing:
            new_type = ItemType(
                id=type_id,
                label="Part BOM Substitute",
                description="Substitute part for a specific BOM line",
                is_relationship=True,
                is_versionable=False,  # Substitutes usually don't have separate versions independent of BOM
            )
            self.session.add(new_type)
            self.session.commit()

    def add_substitute(
        self,
        bom_line_id: str,
        substitute_item_id: str,
        properties: Optional[Dict[str, Any]] = None,
        user_id: int = 1,
    ) -> Item:
        """
        Add a substitute part to a BOM line.
        """
        self.permission_service.check_permission(
            user_id, "create", "Part BOM Substitute"
        )
        self.ensure_substitute_item_type()

        # Verify BOM line exists
        bom_line = self.session.get(Item, bom_line_id)
        if not bom_line or bom_line.item_type_id not in [
            "Part BOM",
            "Manufacturing BOM",
        ]:
            raise ValueError(f"Invalid BOM Line ID: {bom_line_id}")

        # Verify Substitute Item exists
        sub_item = self.session.get(Item, substitute_item_id)
        if not sub_item:
            raise ValueError(f"Substitute Item ID not found: {substitute_item_id}")

        existing = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == "Part BOM Substitute",
                Item.source_id == bom_line_id,
                Item.related_id == substitute_item_id,
                Item.is_current.is_(True),
            )
            .first()
        )
        if existing:
            raise ValueError(
                "Substitute already exists for this BOM line and item"
            )

        # Create Substitute Relationship
        sub_rel = Item(
            id=str(uuid.uuid4()),
            item_type_id="Part BOM Substitute",
            config_id=str(uuid.uuid4()),
            generation=1,
            is_current=True,
            state="Active",
            source_id=bom_line_id,
            related_id=substitute_item_id,
            properties=properties or {},
            created_by_id=user_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(sub_rel)
        self.session.commit()
        return sub_rel

    def get_bom_substitutes(self, bom_line_id: str) -> List[Dict[str, Any]]:
        """
        Get all substitutes for a specific BOM line.
        """
        subs = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == "Part BOM Substitute",
                Item.source_id == bom_line_id,
                Item.is_current.is_(True),
            )
            .all()
        )

        result = []
        for sub in subs:
            # Fetch details of the substitute part
            part = self.session.get(Item, sub.related_id)
            if part:
                part_data = part.to_dict()
                sub_dict = sub.to_dict()
                sub_props = sub.properties or {}
                # Include properties in relationship dict for backward compatibility
                sub_dict["properties"] = sub_props
                # Return format supporting both test expectations
                result.append(
                    {
                        "id": sub.id,
                        "substitute_part": part_data,  # For test_substitutes.py
                        "rank": sub_props.get("rank"),  # For test_substitutes.py
                        "relationship": sub_dict,  # For test_substitute_management.py
                        "part": part_data,  # Keep for backwards compatibility
                    }
                )
        return result

    # Method aliases for backward compatibility with tests
    def add_bom_substitute(
        self,
        bom_relationship_id: str,
        substitute_item_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Item:
        """Alias for add_substitute with different parameter name."""
        return self.add_substitute(
            bom_line_id=bom_relationship_id,
            substitute_item_id=substitute_item_id,
            properties=properties,
            user_id=int(self.user_id) if self.user_id else 1,
        )

    def remove_substitute(self, substitute_rel_id: str, user_id: int):
        """
        Remove a substitute relationship.
        """
        self.permission_service.check_permission(
            user_id, "delete", "Part BOM Substitute", resource_id=substitute_rel_id
        )

        sub = self.session.get(Item, substitute_rel_id)
        if not sub:
            raise ValueError(f"Substitute relationship {substitute_rel_id} not found")

        self.session.delete(sub)
        self.session.commit()
