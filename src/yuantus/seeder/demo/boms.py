import uuid
import random
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.relationship.models import Relationship
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class BOMDemoSeeder(BaseSeeder):
    """Seeds random BOM structures."""
    priority = 600  # Run after Items (500)

    def run(self):
        # Check if BOM data already exists
        if self.session.query(Relationship).filter_by(relationship_type_id="PartBOM").count() > 0:
            self.log("BOM data already exists. Skipping.")
            return

        # Get all existing Parts
        parts = self.session.query(Item).filter_by(item_type_id="Part").all()
        if len(parts) < 10:
            self.log("Not enough parts to generate BOMs. Skipping.")
            return

        # Randomly select 20% of parts as assemblies
        assemblies = random.sample(parts, k=int(len(parts) * 0.2))

        relationships = []
        self.log(f"Generating BOMs for {len(assemblies)} assemblies...")

        for parent in assemblies:
            # Each assembly has 3-8 children
            # Exclude self to avoid direct cyclic
            potential_children = [p for p in parts if p.id != parent.id]
            children = random.sample(potential_children, k=random.randint(3, 8))

            for index, child in enumerate(children):
                rel = Relationship(
                    id=str(uuid.uuid4()),
                    relationship_type_id="PartBOM",
                    source_id=parent.id,
                    related_id=child.id,
                    sort_order=index * 10,
                    properties={
                        "quantity": random.randint(1, 10),
                        "unit": "EA"
                    }
                )
                relationships.append(rel)

        self.session.bulk_save_objects(relationships)
        self.log(f"Generated {len(relationships)} BOM relationships.")
