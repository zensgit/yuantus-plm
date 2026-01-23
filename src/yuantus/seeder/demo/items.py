import uuid
from yuantus.meta_engine.models.item import Item
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class ItemDemoSeeder(BaseSeeder):
    """Seeds demo items."""
    priority = 500

    def run(self):
        if self.session.query(Item).count() > 0:
            self.log("Items already exist. Skipping demo generation.")
            return

        count = 100
        items = []
        self.log(f"Generating {count} demo items...")

        for _ in range(count):
            part_no = self.fake.bothify(text='PRT-####-????').upper()
            item_uuid = str(uuid.uuid4())

            # Create the Item
            # Note: In a real system, we'd also create ItemVersion, but for seeding
            # raw meta_items table, we adhere to the basic schema.
            item = Item(
                id=item_uuid,
                item_type_id="Part",  # Depends on MetaSchemaSeeder
                config_id=str(uuid.uuid4()), # Master ID
                generation=1,
                is_current=True,

                # Lifecycle (Depends on LifecycleSeeder)
                state="Draft",
                current_state="lc_part_std_draft",

                # Dynamic Properties typically go into 'properties' JSONB
                properties={
                    "item_number": part_no,
                    "name": self.fake.sentence(nb_words=3).rstrip('.'),
                    "description": self.fake.text(max_nb_chars=100),
                    "weight": self.fake.random_int(min=1, max=1000)
                }
            )
            items.append(item)

        self.session.bulk_save_objects(items)
        self.log(f"Inserted {count} items.")
