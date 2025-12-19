"""
Bridge between typed tables (PartBOM) and generic relationships
保持向后兼容
Phase 3.3
"""

from sqlalchemy.orm import Session
from sqlalchemy import event

# Assumed import path for PartBOM as per plan, will adjust if needed
# Need to import Item and RelationshipType for the bridge logic
from yuantus.models.bom import (
    BOM,
)  # Assuming PartBOM would be a BOM line or similar, for now using BOM as a placeholder
from yuantus.meta_engine.relationship.models import RelationshipType, Relationship


class PartBOMBridge:
    """
    PartBOM表与通用关系的桥接
    写入part_bom时自动同步到Relationship表
    """

    @staticmethod
    def setup_listeners():
        """设置SQLAlchemy事件监听"""

        # Listener for BOM line inserts/updates to create/update generic relationships
        # This is a conceptual implementation based on the plan's PartBOM example.
        # It needs to be adapted to the actual BOM structure (BOM, BOMLine, etc.)
        @event.listens_for(
            BOM, "after_insert"
        )  # Using BOM as placeholder, replace with actual PartBOM model
        def sync_bom_to_relationship(mapper, connection, target: BOM):
            """BOM插入后同步到relationship - 概念性实现"""
            # This is a simplified conceptual sync.
            # A real implementation would involve:
            # 1. Creating Item entries for the BOM itself and its lines if they don't exist.
            # 2. Creating Relationship entries for BOM structure (e.g., Parent BOM -> Child Product).

            # Example: Create a "BOM_PART" relationship between a Product and its BOM
            try:
                # Need a session to query/create. Direct connection might be tricky here.
                # In a real app, this would likely be handled by a service.
                session = Session(bind=connection)

                # Assume a "Part_BOM" RelationshipType exists or create it
                rel_type_name = "BOM_PART"
                rel_type = (
                    session.query(RelationshipType)
                    .filter_by(name=rel_type_name)
                    .first()
                )
                if not rel_type:
                    # Create a default relationship type if not found
                    rel_type = RelationshipType(
                        id=rel_type_name,
                        name=rel_type_name,
                        label="BOM Contains Part",
                        source_item_type="Product",  # Assuming BOM belongs to Product
                        related_item_type="BOM",
                        is_polymorphic=False,
                    )
                    session.add(rel_type)
                    session.flush()  # Ensure rel_type has an ID

                # Create a Relationship representing Product has BOM
                # Assuming target.product_id maps to an Item
                # For this to work, Product and BOM must also be Items.

                # This part is highly dependent on how Product/BOM are mapped to MetaEngine.
                # If Product and BOM are "Items" in meta_items table:
                # product_item = session.query(Item).filter_by(id=str(target.product_id)).first()
                # bom_item = session.query(Item).filter_by(id=str(target.id)).first()

                # If target.product.id corresponds to an Item id (string):
                product_item_id = str(target.product_id)  # Example
                bom_item_id = str(target.id)  # Example

                existing_rel = (
                    session.query(Relationship)
                    .filter_by(
                        relationship_type_id=rel_type.id,
                        source_id=product_item_id,
                        related_id=bom_item_id,
                    )
                    .first()
                )

                if not existing_rel:
                    relationship = Relationship(
                        relationship_type_id=rel_type.id,
                        source_id=product_item_id,
                        related_id=bom_item_id,
                        properties={"notes": "Automatically created from BOM insert"},
                    )
                    session.add(relationship)
                session.commit()
            except Exception as e:
                session.rollback()
                event.nfo(f"Error syncing BOM to generic relationship: {e}")

        # Listener for BOM line deletes to remove generic relationships
        @event.listens_for(BOM, "after_delete")  # Using BOM as placeholder
        def remove_bom_from_relationship(mapper, connection, target: BOM):
            """BOM删除后移除relationship - 概念性实现"""
            try:
                session = Session(bind=connection)
                rel_type_name = "BOM_PART"

                # Need to find relationships related to this BOM
                session.query(Relationship).filter(
                    Relationship.related_id
                    == str(target.id),  # Assuming BOM ID is target.id
                    Relationship.relationship_type.has(
                        RelationshipType.name == rel_type_name
                    ),
                ).delete(synchronize_session=False)
                session.commit()
            except Exception as e:
                session.rollback()
                event.nfo(f"Error removing BOM from generic relationship: {e}")

        # Note: The original plan snippet had PartBOM specific listeners
        # @event.listens_for(PartBOM, "after_insert")
        # def sync_to_relationship(mapper, connection, target):
        # ...
        # This implementation uses BOM as a generic example.
        # It needs refinement once the actual PartBOM model is clear and integrated with MetaEngine.
