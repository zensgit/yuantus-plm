import sys
import os
import argparse
import logging
from typing import Dict, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from yuantus.config import get_settings
from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_sessionmaker_for_scope, SessionLocal
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.models import Relationship, RelationshipType


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("yuantus.migrate.relationships")


def _open_session(tenant: Optional[str], org: Optional[str]):
    settings = get_settings()
    if settings.TENANCY_MODE in ("db-per-tenant", "db-per-tenant-org"):
        if not tenant:
            raise SystemExit("TENANCY_MODE requires --tenant")
        tenant_id_var.set(tenant)
        if settings.TENANCY_MODE == "db-per-tenant-org":
            if not org:
                raise SystemExit("TENANCY_MODE=db-per-tenant-org requires --org")
            org_id_var.set(org)
        session_factory = get_sessionmaker_for_scope(tenant, org)
        return session_factory()
    return SessionLocal()


def _ensure_relationship_item_types(session, rel_types, allow_updates: bool) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for rel_type in rel_types:
        item_type_id = rel_type.name or rel_type.id
        mapping[rel_type.id] = item_type_id
        item_type = session.query(ItemType).filter(ItemType.id == item_type_id).first()
        if not item_type:
            item_type = ItemType(
                id=item_type_id,
                label=rel_type.label or rel_type.name or rel_type.id,
                description=f"Relationship type for {rel_type.name or rel_type.id}",
                is_relationship=True,
                is_versionable=False,
                version_control_enabled=False,
                source_item_type_id=rel_type.source_item_type,
                related_item_type_id=rel_type.related_item_type,
            )
            session.add(item_type)
            logger.info("Created ItemType for relationship: %s", item_type_id)
        elif allow_updates:
            changed = False
            if not item_type.is_relationship:
                item_type.is_relationship = True
                changed = True
            if not item_type.source_item_type_id:
                item_type.source_item_type_id = rel_type.source_item_type
                changed = True
            if not item_type.related_item_type_id:
                item_type.related_item_type_id = rel_type.related_item_type
                changed = True
            if changed:
                logger.info("Updated ItemType metadata: %s", item_type_id)
    return mapping


def _count_missing(session, rel_type_missing: bool) -> Dict[str, int]:
    missing = {}
    if rel_type_missing:
        missing["missing_type"] = (
            session.query(Relationship)
            .outerjoin(
                RelationshipType,
                Relationship.relationship_type_id == RelationshipType.id,
            )
            .filter(RelationshipType.id.is_(None))
            .count()
        )
    missing["missing_source"] = (
        session.query(Relationship)
        .outerjoin(Item, Relationship.source_id == Item.id)
        .filter(Item.id.is_(None))
        .count()
    )
    missing["missing_related"] = (
        session.query(Relationship)
        .outerjoin(Item, Relationship.related_id == Item.id)
        .filter(Item.id.is_(None))
        .count()
    )
    return missing


def _migrate(session, mapping: Dict[str, str], dry_run: bool, allow_orphans: bool) -> int:
    migrated = 0
    query = (
        session.query(Relationship)
        .outerjoin(Item, Item.id == Relationship.id)
        .filter(Item.id.is_(None))
    )
    for rel in query.yield_per(500):
        item_type_id = mapping.get(rel.relationship_type_id)
        if not item_type_id:
            if allow_orphans:
                logger.warning("Skip relationship %s: missing type %s", rel.id, rel.relationship_type_id)
                continue
            raise RuntimeError(f"Missing relationship type for {rel.id}: {rel.relationship_type_id}")

        source_item = session.get(Item, rel.source_id) if rel.source_id else None
        related_item = session.get(Item, rel.related_id) if rel.related_id else None
        if (not source_item or not related_item) and not allow_orphans:
            raise RuntimeError(
                f"Missing source/related for {rel.id}: source={rel.source_id} related={rel.related_id}"
            )
        if not source_item or not related_item:
            logger.warning(
                "Skip relationship %s: source=%s related=%s",
                rel.id,
                rel.source_id,
                rel.related_id,
            )
            continue

        props = dict(rel.properties or {})
        if rel.sort_order is not None and "sort_order" not in props:
            props["sort_order"] = rel.sort_order

        item = Item(
            id=rel.id,
            item_type_id=item_type_id,
            config_id=rel.id,
            generation=1,
            is_current=True,
            state=rel.state or "Active",
            source_id=rel.source_id,
            related_id=rel.related_id,
            properties=props,
            created_by_id=rel.created_by_id,
            permission_id=getattr(source_item, "permission_id", None),
        )
        session.add(item)
        migrated += 1

        if not dry_run and migrated % 500 == 0:
            session.flush()
            session.commit()

    if not dry_run:
        session.commit()
    else:
        session.rollback()
    return migrated


def main():
    parser = argparse.ArgumentParser(description="Migrate meta_relationships into meta_items.")
    parser.add_argument("--tenant", help="Tenant ID for multi-tenant modes", default=None)
    parser.add_argument("--org", help="Org ID for db-per-tenant-org mode", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    parser.add_argument("--allow-orphans", action="store_true", help="Skip rows with missing type/source/related")
    parser.add_argument("--update-item-types", action="store_true", help="Update existing ItemType metadata")
    args = parser.parse_args()

    session = _open_session(args.tenant, args.org)
    try:
        rel_total = session.query(Relationship).count()
        rel_type_total = session.query(RelationshipType).count()
        existing = (
            session.query(Relationship)
            .join(Item, Item.id == Relationship.id)
            .count()
        )

        missing = _count_missing(session, rel_type_total > 0)

        logger.info("Relationships: total=%s existing_items=%s", rel_total, existing)
        logger.info("Missing type=%s source=%s related=%s", missing.get("missing_type", 0), missing["missing_source"], missing["missing_related"])

        if not args.allow_orphans:
            if missing.get("missing_type", 0) > 0:
                raise RuntimeError("Missing relationship types; rerun with --allow-orphans or fix data")
            if missing["missing_source"] > 0 or missing["missing_related"] > 0:
                raise RuntimeError("Missing source/related items; rerun with --allow-orphans or fix data")

        rel_types = session.query(RelationshipType).all()
        mapping = _ensure_relationship_item_types(session, rel_types, args.update_item_types)
        if args.dry_run:
            session.rollback()
        else:
            session.commit()

        migrated = _migrate(session, mapping, args.dry_run, args.allow_orphans)
        logger.info("Migrated relationship items: %s", migrated)
    finally:
        session.close()


if __name__ == "__main__":
    main()
