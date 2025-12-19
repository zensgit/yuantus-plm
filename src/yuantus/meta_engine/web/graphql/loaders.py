"""
DataLoader Implementations for GraphQL Meta Engine (ADR-007)

Uses DataLoader pattern to batch database queries and prevent N+1 problems.
"""

from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from .types import (
    Part,
    Document,
    BOMLine,
    ECO,
    ECOStage,
    ECOApproval,
    ECOBOMChange,
    GenericItem,
    ItemVersion,
    FileAttachment,
    User,
    WhereUsedItem,
)


# ============================================================
# Helper Functions
# ============================================================


def _item_to_part(item) -> Part:
    """Convert Item model to Part GraphQL type."""
    props = item.properties or {}
    return Part(
        id=item.id,
        number=props.get("number") or getattr(item, "number", None),
        name=props.get("name") or getattr(item, "name", None),
        state=item.state,
        generation=item.generation or 1,
        is_current=item.is_current or True,
        config_id=item.config_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        properties=props,
    )


def _item_to_document(item) -> Document:
    """Convert Item model to Document GraphQL type."""
    props = item.properties or {}
    return Document(
        id=item.id,
        number=props.get("number") or getattr(item, "number", None),
        name=props.get("name") or getattr(item, "name", None),
        state=item.state,
        generation=item.generation or 1,
        is_current=item.is_current or True,
        config_id=item.config_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        properties=props,
    )


def _item_to_generic(item) -> GenericItem:
    """Convert Item model to GenericItem GraphQL type."""
    props = item.properties or {}
    return GenericItem(
        id=item.id,
        type=item.item_type_id or "Unknown",
        number=props.get("number") or getattr(item, "number", None),
        name=props.get("name") or getattr(item, "name", None),
        state=item.state,
        generation=item.generation or 1,
        is_current=item.is_current or True,
        config_id=item.config_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        properties=props,
        relationships=None,
    )


def _bom_item_to_line(item, level: int = 1) -> BOMLine:
    """Convert BOM relationship Item to BOMLine GraphQL type."""
    props = item.properties or {}
    return BOMLine(
        id=item.id,
        parent_id=item.source_id,
        child_id=item.related_id,
        quantity=float(props.get("quantity", 1)),
        unit=props.get("unit") or props.get("uom"),
        find_number=props.get("find_number"),
        level=level,
        sequence=props.get("sequence"),
        properties=props,
    )


# ============================================================
# DataLoader Factory Functions
# ============================================================


async def load_parts_by_ids(ids: List[str], db: Session) -> List[Optional[Part]]:
    """
    Batch load Parts by IDs.
    """
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType

    # Get Part ItemType IDs
    part_types = (
        db.execute(
            select(ItemType.id).where(
                and_(
                    ItemType.is_relationship.is_(False),
                    or_(
                        ItemType.id.ilike("part%"),
                        ItemType.id.ilike("%part"),
                    ),
                )
            )
        )
        .scalars()
        .all()
    )

    items = (
        db.execute(
            select(Item).where(
                and_(
                    Item.id.in_(ids),
                    Item.item_type_id.in_(part_types) if part_types else True,
                )
            )
        )
        .scalars()
        .all()
    )

    item_map = {item.id: _item_to_part(item) for item in items}
    return [item_map.get(id) for id in ids]


async def load_documents_by_ids(
    ids: List[str], db: Session
) -> List[Optional[Document]]:
    """
    Batch load Documents by IDs.
    """
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType

    # Get Document ItemType IDs
    doc_types = (
        db.execute(
            select(ItemType.id).where(
                and_(
                    ItemType.is_relationship.is_(False),
                    or_(
                        ItemType.id.ilike("document%"),
                        ItemType.id.ilike("%document"),
                    ),
                )
            )
        )
        .scalars()
        .all()
    )

    items = (
        db.execute(
            select(Item).where(
                and_(
                    Item.id.in_(ids),
                    Item.item_type_id.in_(doc_types) if doc_types else True,
                )
            )
        )
        .scalars()
        .all()
    )

    item_map = {item.id: _item_to_document(item) for item in items}
    return [item_map.get(id) for id in ids]


async def load_generic_items_by_ids(
    ids: List[str], db: Session
) -> List[Optional[GenericItem]]:
    """
    Batch load GenericItems by IDs (any ItemType).
    """
    from yuantus.meta_engine.models.item import Item

    items = db.execute(select(Item).where(Item.id.in_(ids))).scalars().all()

    item_map = {item.id: _item_to_generic(item) for item in items}
    return [item_map.get(id) for id in ids]


async def load_bom_lines_by_parent(
    keys: List[Tuple[str, int]], db: Session
) -> List[List[BOMLine]]:
    """
    Batch load BOM lines by parent ID and depth.

    Keys are tuples of (parent_id, depth).
    """
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType

    # Extract unique parent IDs
    parent_ids = list(set(key[0] for key in keys))

    # Get BOM relationship ItemType
    bom_types = (
        db.execute(
            select(ItemType.id).where(
                and_(
                    ItemType.is_relationship.is_(True),
                    ItemType.id.ilike("%bom%"),
                )
            )
        )
        .scalars()
        .all()
    )

    # Query BOM lines where source_id (parent) is in parent_ids
    bom_items = (
        db.execute(
            select(Item).where(
                and_(
                    Item.source_id.in_(parent_ids),
                    Item.item_type_id.in_(bom_types) if bom_types else True,
                )
            )
        )
        .scalars()
        .all()
    )

    # Group by parent_id
    lines_by_parent: Dict[str, List[BOMLine]] = defaultdict(list)
    for item in bom_items:
        lines_by_parent[item.source_id].append(_bom_item_to_line(item, level=1))

    # Return in same order as keys
    return [lines_by_parent.get(key[0], []) for key in keys]


async def load_where_used(
    keys: List[Tuple[str, int]], db: Session
) -> List[List[WhereUsedItem]]:
    """
    Batch load where-used information (reverse BOM lookup).

    Keys are tuples of (item_id, max_level).
    """
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType

    # Extract unique item IDs
    item_ids = list(set(key[0] for key in keys))

    # Get BOM relationship ItemType
    bom_types = (
        db.execute(
            select(ItemType.id).where(
                and_(
                    ItemType.is_relationship.is_(True),
                    ItemType.id.ilike("%bom%"),
                )
            )
        )
        .scalars()
        .all()
    )

    # Query BOM lines where related_id (child) is in item_ids
    bom_items = (
        db.execute(
            select(Item).where(
                and_(
                    Item.related_id.in_(item_ids),
                    Item.item_type_id.in_(bom_types) if bom_types else True,
                )
            )
        )
        .scalars()
        .all()
    )

    # Get parent item details
    parent_ids = [item.source_id for item in bom_items if item.source_id]
    parent_items = {}
    if parent_ids:
        parents = (
            db.execute(select(Item).where(Item.id.in_(parent_ids))).scalars().all()
        )
        parent_items = {p.id: p for p in parents}

    # Group by child_id
    where_used_by_item: Dict[str, List[WhereUsedItem]] = defaultdict(list)
    for item in bom_items:
        parent = parent_items.get(item.source_id)
        props = item.properties or {}
        parent_props = parent.properties if parent else {}

        where_used_by_item[item.related_id].append(
            WhereUsedItem(
                level=1,
                path=f"{item.source_id}/{item.related_id}",
                parent_id=item.source_id,
                parent_number=parent_props.get("number") if parent else None,
                parent_name=parent_props.get("name") if parent else None,
                quantity=float(props.get("quantity", 1)),
                unit=props.get("unit") or props.get("uom"),
            )
        )

    return [where_used_by_item.get(key[0], []) for key in keys]


async def load_item_versions(ids: List[str], db: Session) -> List[List[ItemVersion]]:
    """
    Batch load item versions.
    """
    from yuantus.meta_engine.version.models import ItemVersion as ItemVersionModel

    versions = (
        db.execute(select(ItemVersionModel).where(ItemVersionModel.item_id.in_(ids)))
        .scalars()
        .all()
    )

    versions_by_item: Dict[str, List[ItemVersion]] = defaultdict(list)
    for v in versions:
        versions_by_item[v.item_id].append(
            ItemVersion(
                id=v.id,
                item_id=v.item_id,
                generation=v.generation or 1,
                revision=v.revision or "A",
                state=v.state,
                created_at=v.created_at,
                created_by_id=v.created_by_id,
            )
        )

    return [versions_by_item.get(id, []) for id in ids]


async def load_document_files(
    ids: List[str], db: Session
) -> List[List[FileAttachment]]:
    """
    Batch load file attachments for documents.
    """
    from yuantus.meta_engine.models.file import File

    files = db.execute(select(File).where(File.item_id.in_(ids))).scalars().all()

    files_by_doc: Dict[str, List[FileAttachment]] = defaultdict(list)
    for f in files:
        files_by_doc[f.item_id].append(
            FileAttachment(
                id=f.id,
                filename=f.filename,
                file_type=f.file_type,
                file_size=f.file_size,
                storage_path=f.storage_path,
                checksum=f.checksum,
                created_at=f.created_at,
            )
        )

    return [files_by_doc.get(id, []) for id in ids]


async def load_ecos_by_ids(ids: List[str], db: Session) -> List[Optional[ECO]]:
    """
    Batch load ECOs by IDs.
    """
    from yuantus.meta_engine.models.eco import ECO as ECOModel

    ecos = db.execute(select(ECOModel).where(ECOModel.id.in_(ids))).scalars().all()

    eco_map = {}
    for e in ecos:
        eco_map[e.id] = ECO(
            id=e.id,
            name=e.name,
            eco_type=e.eco_type,
            product_id=e.product_id,
            stage_id=e.stage_id,
            state=e.state,
            kanban_state=e.kanban_state,
            priority=e.priority,
            description=e.description,
            effectivity_date=e.effectivity_date,
            created_at=e.created_at,
            updated_at=e.updated_at,
            created_by_id=e.created_by_id,
        )

    return [eco_map.get(id) for id in ids]


async def load_eco_stages_by_ids(
    ids: List[str], db: Session
) -> List[Optional[ECOStage]]:
    """
    Batch load ECO stages by IDs.
    """
    from yuantus.meta_engine.models.eco import ECOStage as ECOStageModel

    stages = (
        db.execute(select(ECOStageModel).where(ECOStageModel.id.in_(ids)))
        .scalars()
        .all()
    )

    stage_map = {}
    for s in stages:
        stage_map[s.id] = ECOStage(
            id=s.id,
            name=s.name,
            sequence=s.sequence,
            is_blocking=s.is_blocking,
            approval_type=s.approval_type,
            min_approvals=s.min_approvals,
        )

    return [stage_map.get(id) for id in ids]


async def load_eco_approvals(ids: List[str], db: Session) -> List[List[ECOApproval]]:
    """
    Batch load ECO approvals by ECO ID.
    """
    from yuantus.meta_engine.models.eco import ECOApproval as ECOApprovalModel

    approvals = (
        db.execute(select(ECOApprovalModel).where(ECOApprovalModel.eco_id.in_(ids)))
        .scalars()
        .all()
    )

    approvals_by_eco: Dict[str, List[ECOApproval]] = defaultdict(list)
    for a in approvals:
        approvals_by_eco[a.eco_id].append(
            ECOApproval(
                id=a.id,
                eco_id=a.eco_id,
                stage_id=a.stage_id,
                status=a.status,
                user_id=a.user_id,
                comment=a.comment,
                approved_at=a.approved_at,
                created_at=a.created_at,
            )
        )

    return [approvals_by_eco.get(id, []) for id in ids]


async def load_eco_bom_changes(ids: List[str], db: Session) -> List[List[ECOBOMChange]]:
    """
    Batch load ECO BOM changes by ECO ID.
    """
    from yuantus.meta_engine.models.eco import ECOBOMChange as ECOBOMChangeModel

    changes = (
        db.execute(select(ECOBOMChangeModel).where(ECOBOMChangeModel.eco_id.in_(ids)))
        .scalars()
        .all()
    )

    changes_by_eco: Dict[str, List[ECOBOMChange]] = defaultdict(list)
    for c in changes:
        changes_by_eco[c.eco_id].append(
            ECOBOMChange(
                id=c.id,
                eco_id=c.eco_id,
                change_type=c.change_type,
                parent_item_id=c.parent_item_id,
                child_item_id=c.child_item_id,
                old_qty=c.old_qty,
                new_qty=c.new_qty,
                old_uom=c.old_uom,
                new_uom=c.new_uom,
                conflict=c.conflict,
                conflict_reason=c.conflict_reason,
            )
        )

    return [changes_by_eco.get(id, []) for id in ids]


async def load_users_by_ids(ids: List[int], db: Session) -> List[Optional[User]]:
    """
    Batch load users by IDs.
    """
    from yuantus.security.rbac.models import RBACUser

    users = db.execute(select(RBACUser).where(RBACUser.id.in_(ids))).scalars().all()

    user_map = {}
    for u in users:
        user_map[u.id] = User(
            id=u.id,
            username=u.username,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
        )

    return [user_map.get(id) for id in ids]


async def load_part_documents(ids: List[str], db: Session) -> List[List[Document]]:
    """
    Batch load documents related to parts.
    """
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType

    # Get document-part relationship ItemType
    rel_types = (
        db.execute(
            select(ItemType.id).where(
                and_(
                    ItemType.is_relationship.is_(True),
                    or_(
                        ItemType.id.ilike("%document%part%"),
                        ItemType.id.ilike("%part%document%"),
                    ),
                )
            )
        )
        .scalars()
        .all()
    )

    # Query relationships
    relations = (
        db.execute(
            select(Item).where(
                and_(
                    Item.source_id.in_(ids),
                    Item.item_type_id.in_(rel_types) if rel_types else False,
                )
            )
        )
        .scalars()
        .all()
    )

    # Get document IDs
    doc_ids = [r.related_id for r in relations if r.related_id]

    # Load documents
    docs = {}
    if doc_ids:
        doc_items = db.execute(select(Item).where(Item.id.in_(doc_ids))).scalars().all()
        docs = {d.id: _item_to_document(d) for d in doc_items}

    # Group by part_id
    docs_by_part: Dict[str, List[Document]] = defaultdict(list)
    for r in relations:
        if r.related_id and r.related_id in docs:
            docs_by_part[r.source_id].append(docs[r.related_id])

    return [docs_by_part.get(id, []) for id in ids]


async def load_document_parts(ids: List[str], db: Session) -> List[List[Part]]:
    """
    Batch load parts related to documents.
    """
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType

    # Get document-part relationship ItemType
    rel_types = (
        db.execute(
            select(ItemType.id).where(
                and_(
                    ItemType.is_relationship.is_(True),
                    or_(
                        ItemType.id.ilike("%document%part%"),
                        ItemType.id.ilike("%part%document%"),
                    ),
                )
            )
        )
        .scalars()
        .all()
    )

    # Query relationships (reverse lookup)
    relations = (
        db.execute(
            select(Item).where(
                and_(
                    Item.related_id.in_(ids),
                    Item.item_type_id.in_(rel_types) if rel_types else False,
                )
            )
        )
        .scalars()
        .all()
    )

    # Get part IDs
    part_ids = [r.source_id for r in relations if r.source_id]

    # Load parts
    parts = {}
    if part_ids:
        part_items = (
            db.execute(select(Item).where(Item.id.in_(part_ids))).scalars().all()
        )
        parts = {p.id: _item_to_part(p) for p in part_items}

    # Group by document_id
    parts_by_doc: Dict[str, List[Part]] = defaultdict(list)
    for r in relations:
        if r.source_id and r.source_id in parts:
            parts_by_doc[r.related_id].append(parts[r.source_id])

    return [parts_by_doc.get(id, []) for id in ids]


# ============================================================
# DataLoader Factory
# ============================================================


def create_data_loaders(db: Session) -> Dict[str, Any]:
    """
    Create all DataLoaders for GraphQL context.
    """
    from strawberry.dataloader import DataLoader

    return {
        "part_loader": DataLoader(load_fn=lambda ids: load_parts_by_ids(ids, db)),
        "document_loader": DataLoader(
            load_fn=lambda ids: load_documents_by_ids(ids, db)
        ),
        "generic_item_loader": DataLoader(
            load_fn=lambda ids: load_generic_items_by_ids(ids, db)
        ),
        "bom_lines_loader": DataLoader(
            load_fn=lambda keys: load_bom_lines_by_parent(keys, db)
        ),
        "where_used_loader": DataLoader(load_fn=lambda keys: load_where_used(keys, db)),
        "item_versions_loader": DataLoader(
            load_fn=lambda ids: load_item_versions(ids, db)
        ),
        "document_files_loader": DataLoader(
            load_fn=lambda ids: load_document_files(ids, db)
        ),
        "eco_loader": DataLoader(load_fn=lambda ids: load_ecos_by_ids(ids, db)),
        "eco_stage_loader": DataLoader(
            load_fn=lambda ids: load_eco_stages_by_ids(ids, db)
        ),
        "eco_approvals_loader": DataLoader(
            load_fn=lambda ids: load_eco_approvals(ids, db)
        ),
        "eco_bom_changes_loader": DataLoader(
            load_fn=lambda ids: load_eco_bom_changes(ids, db)
        ),
        "user_loader": DataLoader(load_fn=lambda ids: load_users_by_ids(ids, db)),
        "part_documents_loader": DataLoader(
            load_fn=lambda ids: load_part_documents(ids, db)
        ),
        "document_parts_loader": DataLoader(
            load_fn=lambda ids: load_document_parts(ids, db)
        ),
    }
