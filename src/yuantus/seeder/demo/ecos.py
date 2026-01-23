import uuid
import random
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.eco import ECO, ECOPriority, ECOBOMChange
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class ECODemoSeeder(BaseSeeder):
    """Seeds demo Engineering Change Orders."""
    priority = 700  # After BOMs (600)

    def run(self):
        if self.session.query(ECO).count() > 0:
            self.log("ECOs already exist. Skipping.")
            return

        # Get parts that are assemblies (have children)
        # Using a subquery-like logic in python for simplicity
        # Find Parts that are source_id in PartBOM relationships
        assembly_ids = [
            row[0]
            for row in self.session.query(Item.source_id)
            .filter(
                Item.item_type_id == "Part BOM",
                Item.source_id.isnot(None),
            )
            .distinct()
        ]

        if not assembly_ids:
            self.log("No assemblies found to create ECOs for.")
            return

        # Pick 5 random assemblies to change
        target_ids = random.sample(assembly_ids, k=min(5, len(assembly_ids)))

        count = 0
        self.log(f"Creating ECOs for {len(target_ids)} assemblies...")

        for prod_id in target_ids:
            count += 1
            eco_id = f"ECO-2024-{1000+count}"

            # Create ECO Header
            eco = ECO(
                id=eco_id,
                name=f"Update BOM for {prod_id[:8]}...",
                product_id=prod_id,
                state="draft",
                stage_id="stage_eco_draft", # Default to draft
                priority=random.choice(list(ECOPriority)),
                description=self.fake.text(),
                eco_type="bom"
            )
            self.session.add(eco)

            # Create a BOM Change (Update Quantity)
            # Find a child relationship
            rel = (
                self.session.query(Item)
                .filter(
                    Item.item_type_id == "Part BOM",
                    Item.source_id == prod_id,
                    Item.is_current.is_(True),
                )
                .first()
            )
            if rel:
                old_qty = 1.0
                if rel.properties and 'quantity' in rel.properties:
                    old_qty = float(rel.properties['quantity'])

                change = ECOBOMChange(
                    id=str(uuid.uuid4()),
                    eco_id=eco_id,
                    change_type="update",
                    relationship_item_id=rel.id,
                    parent_item_id=prod_id,
                    child_item_id=rel.related_id,
                    old_qty=old_qty,
                    new_qty=float(random.randint(10, 20))
                )
                self.session.add(change)

        self.session.commit() # Commit explicitly to ensure IDs are valid
        self.log(f"Generated {count} ECOs with BOM changes.")
