from yuantus.config import get_settings
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.models import RelationshipType
from yuantus.seeder.base import BaseSeeder
from yuantus.seeder.registry import SeederRegistry

@SeederRegistry.register
class MetaSchemaSeeder(BaseSeeder):
    """Seeds standard ItemTypes (Part, Document) and RelationshipTypes."""
    priority = 150  # Run before Lifecycle (200) and Demo (500)

    def run(self):
        settings = get_settings()
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

        # 3. BOM Relationship Type (legacy optional)
        if settings.RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED:
            self._ensure_rel_type(
                id="PartBOM",
                name="Part BOM",
                label="Part BOM",
                source_type="Part",
                related_type="Part"
            )
        else:
            self.log("Skipping RelationshipType seeding (legacy disabled)")
        # 4. BOM Relationship ItemType (关系即 Item)
        self._ensure_item_type(
            id="Part BOM",
            label="Part BOM",
            is_versionable=False,
            icon="link"
        )
        bom_item_type = self.session.query(ItemType).filter_by(id="Part BOM").first()
        if bom_item_type:
            bom_item_type.is_relationship = True
            if not bom_item_type.source_item_type_id:
                bom_item_type.source_item_type_id = "Part"
            if not bom_item_type.related_item_type_id:
                bom_item_type.related_item_type_id = "Part"

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

    def _ensure_rel_type(self, id, name, label, source_type, related_type):
        rt = self.session.query(RelationshipType).filter_by(id=id).first()
        if not rt:
            rt = RelationshipType(
                id=id,
                name=name,
                label=label,
                source_item_type=source_type,
                related_item_type=related_type,
                max_quantity=None  # Unlimited children
            )
            self.session.add(rt)
            self.log(f"Created RelationshipType: {name}")
        return rt
