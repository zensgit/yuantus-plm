"""
Change Management Service (ECM)
Handles Impact Analysis, Affected Items, and ECO Execution.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.version.service import VersionService
from yuantus.meta_engine.services.bom_service import BOMService


class ChangeService:
    def __init__(self, session: Session):
        self.session = session
        self.version_service = VersionService(session)
        self.bom_service = BOMService(session)

    def get_impact_analysis(self, item_id: str) -> Dict[str, Any]:
        """
        Analyze impact of changing an item.
        Returns Where Used information and Open Pending Changes.
        """
        # 1. Where Used
        where_used = self.bom_service.get_where_used(item_id)

        # 2. Open Changes (Pending ECR/ECOs affecting this item)
        # Search for Affected Items linking to this item
        pending_rels = (
            self.session.query(Item)
            .filter(
                Item.item_type_id == "Affected Item",
                Item.related_id == item_id,
                # Ideally filter by ECO State not being Closed/Released
                # But we don't have easy join to Source Item State yet without more complex query
            )
            .all()
        )

        pending_changes = []
        for rel in pending_rels:
            eco = self.session.get(Item, rel.source_id)
            if eco and eco.state != "Released":
                pending_changes.append(eco.to_dict())

        return {"where_used": where_used, "pending_changes": pending_changes}

    def get_affected_items(self, eco_id: str) -> List[Item]:
        """
        Retrieves all Affected Items for a given ECO.
        """
        # Affected Item is a Relationship ItemType.
        # Source ID = ECO ID.
        # We query the 'Item' table where item_type_id='Affected Item' and source_id=eco_id

        return (
            self.session.query(Item)
            .filter(Item.item_type_id == "Affected Item", Item.source_id == eco_id)
            .all()
        )

    def add_affected_item(
        self, eco_id: str, target_item_id: str, action: str = "Change"
    ) -> Item:
        """
        Adds an item to the ECO.
        """
        import uuid
        from datetime import datetime

        # Verify ECO and Target exist
        eco = self.session.query(Item).filter_by(id=eco_id).first()
        target = self.session.query(Item).filter_by(id=target_item_id).first()

        if not eco or not target:
            raise ValueError("ECO or Target Item not found")

        rel_id = str(uuid.uuid4())
        affected_item = Item(
            id=rel_id,
            item_type_id="Affected Item",
            source_id=eco_id,
            related_id=target_item_id,
            properties={"action": action},
            created_at=datetime.utcnow(),
        )
        self.session.add(affected_item)
        return affected_item

    def execute_eco(self, eco_id: str, user_id: int):
        """
        Executes the ECO:
        - For each affected item, performs the action (e.g., Release).
        """
        affected = self.get_affected_items(eco_id)

        for aff in affected:
            action = aff.properties.get("action", "Change")
            target_id = aff.related_id

            if action == "Release":
                # Release the current version of the target item
                # Or release the *specific* version linked (if we linked version).
                # Assuming target_id is the Item ID, we release its current version?
                # Usually ECO releases the "In Work" version.

                # Logic: Find current version, check if it's Draft/InWork, then set to Released.
                target_item = self.session.query(Item).filter_by(id=target_id).first()
                if target_item and target_item.current_version_id:
                    self._release_version(target_item.current_version_id, user_id)

            elif action == "Revise":
                # Create a new revision
                self.version_service.revise(
                    target_id, user_id, comment=f"Revised by ECO {eco_id}"
                )

            elif action == "New Generation":
                # Create a new generation
                self.version_service.new_generation(
                    target_id, user_id, comment=f"New Generation by ECO {eco_id}"
                )

    def _release_version(self, version_id: str, user_id: int):
        from yuantus.meta_engine.version.models import ItemVersion
        from datetime import datetime

        ver = self.session.query(ItemVersion).get(version_id)
        if ver:
            ver.state = "Released"
            ver.is_released = True
            ver.released_at = datetime.utcnow()
            ver.released_by_id = user_id
            self.session.add(ver)
