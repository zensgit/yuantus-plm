import uuid
from yuantus.meta_engine.models.item import Item
from yuantus.seeder.file_loader import BaseFileSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class StandardPartSeeder(BaseFileSeeder):
    """Seeds official standard parts from JSON."""
    priority = 300  # Production Data

    def run(self):
        # Load data from src/yuantus/seeder/data/standard_parts.json
        parts_data = self.load_json("standard_parts.json")
        if not parts_data:
            return

        imported_count = 0
        for p in parts_data:
            part_number = p.get('part_number')
            if not part_number:
                continue

            # Check existence (Idempotency)
            # Use part_number as ID for standard parts
            existing = self.session.query(Item).filter_by(id=part_number).first()

            if not existing:
                item = Item(
                    id=part_number,
                    item_type_id="Part",
                    config_id=str(uuid.uuid4()),
                    generation=1,
                    is_current=True,
                    state="Released", # Standard parts are usually released
                    current_state="lc_part_std_released",
                    # Depends on LifecycleSeeder creating 'lc_part_std_released'

                    properties={
                        "item_number": part_number,
                        "name": p.get('name'),
                        "description": p.get('description'),
                        "material": p.get('material'),
                        "standard": p.get('standard')
                    }
                )
                self.session.add(item)
                imported_count += 1

        self.log(f"Imported {imported_count} new standard parts.")
