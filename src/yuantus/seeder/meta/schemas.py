from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class MetaSchemaSeeder(BaseSeeder):
    """Seeds standard ItemTypes (Part, Document)."""
    priority = 150  # Run before Lifecycle (200) and Demo (500)

    def run(self):
        # 1. Standard Part Type
        self._ensure_item_type(
            id="Part",
            label="Part",
            is_versionable=True,
            icon="box"
        )

        # 2. Document Type
        self._ensure_item_type(
            id="Document",
            label="Document",
            is_versionable=True,
            icon="file-text"
        )

    def _ensure_item_type(self, id: str, label: str, is_versionable: bool = True, icon: str = None):
        it = self.session.query(ItemType).filter_by(id=id).first()
        if not it:
            it = ItemType(
                id=id,
                label=label,
                description=f"Standard {label} type",
                is_versionable=is_versionable,
                # Store extra UI metadata in ui_layout if needed
                ui_layout={"icon": icon} if icon else {}
            )
            self.session.add(it)
            self.log(f"Created ItemType: {label}")
        return it
