"""Contracts for WP1.1 CAD-PDM relationship ItemType seeds."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.service import RelationshipService
from yuantus.models import user as _user  # noqa: F401 - registers users table
from yuantus.models.base import Base
from yuantus.seeder.meta.schemas import MetaSchemaSeeder

import_all_models()


CAD_PDM_RELATIONSHIP_TYPES = {"ASSEMBLY", "REFERENCE"}
FORBIDDEN_DOCUMENT_RELATIONSHIP_TYPES = {
    "DOC_ASSEMBLY",
    "DOC_2D3D",
    "DOC_REFERENCE",
    "DOC_PACKAGE",
    "DRAWING_OF",
    "PACKAGE",
}


@pytest.fixture()
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pdm-relationship-types.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    db = SessionLocal()
    yield db
    db.close()


def _seed_meta_schema(session) -> None:
    MetaSchemaSeeder(session).run()
    session.commit()


def _item(session, item_id: str, item_type_id: str = "Part") -> Item:
    item = Item(
        id=item_id,
        item_type_id=item_type_id,
        config_id=f"cfg-{item_id}-{uuid.uuid4()}",
        generation=1,
        is_current=True,
        state="Active",
        properties={"item_number": item_id},
    )
    session.add(item)
    return item


def test_wp1_1_seeds_only_assembly_and_reference_relationship_item_types(session):
    _seed_meta_schema(session)

    for type_id in CAD_PDM_RELATIONSHIP_TYPES:
        item_type = session.get(ItemType, type_id)
        assert item_type is not None
        assert item_type.is_relationship is True
        assert item_type.is_versionable is False
        assert item_type.source_item_type_id == "Part"
        assert item_type.related_item_type_id == "Part"

    for forbidden_type_id in FORBIDDEN_DOCUMENT_RELATIONSHIP_TYPES:
        assert session.get(ItemType, forbidden_type_id) is None


def test_wp1_1_relationship_type_seed_is_idempotent_and_corrects_endpoints(session):
    session.add_all(
        [
            ItemType(id="Part", label="Part", is_versionable=True),
            ItemType(id="ASSEMBLY", label="Stale", is_versionable=True),
        ]
    )
    session.commit()

    _seed_meta_schema(session)
    _seed_meta_schema(session)

    rows = session.query(ItemType).filter(ItemType.id == "ASSEMBLY").all()
    assert len(rows) == 1
    assembly = rows[0]
    assert assembly.label == "Assembly"
    assert assembly.is_relationship is True
    assert assembly.is_versionable is False
    assert assembly.source_item_type_id == "Part"
    assert assembly.related_item_type_id == "Part"


def test_wp1_1_assembly_relationship_allows_part_to_part_and_is_queryable(session):
    _seed_meta_schema(session)
    _item(session, "ASSY")
    _item(session, "CHILD")
    session.commit()

    service = RelationshipService(session)
    relationship = service.create_relationship(
        "ASSY",
        "CHILD",
        "ASSEMBLY",
        properties={"position": "001", "config": "default"},
    )

    assert relationship.item_type_id == "ASSEMBLY"
    assert relationship.source_id == "ASSY"
    assert relationship.related_id == "CHILD"
    assert relationship.properties == {"position": "001", "config": "default"}

    outgoing = service.get_relationships(
        "ASSY",
        direction="outgoing",
        relationship_type_name="ASSEMBLY",
    )
    assert [edge.id for edge in outgoing] == [relationship.id]


def test_wp1_1_reference_relationship_allows_part_to_part_and_is_queryable(session):
    _seed_meta_schema(session)
    _item(session, "PART-A")
    _item(session, "PART-B")
    session.commit()

    service = RelationshipService(session)
    relationship = service.create_relationship(
        "PART-A",
        "PART-B",
        "REFERENCE",
        properties={"reference_type": "external"},
    )

    incoming = service.get_relationships(
        "PART-B",
        direction="incoming",
        relationship_type_name="REFERENCE",
    )
    assert [edge.id for edge in incoming] == [relationship.id]


def test_wp1_1_relationship_types_reject_non_part_endpoints(session):
    _seed_meta_schema(session)
    _item(session, "PART")
    _item(session, "DOC", item_type_id="Document")
    session.commit()

    service = RelationshipService(session)

    with pytest.raises(ValueError, match="Source type mismatch: expected Part"):
        service.create_relationship("DOC", "PART", "ASSEMBLY")

    with pytest.raises(ValueError, match="Related type mismatch: expected Part"):
        service.create_relationship("PART", "DOC", "REFERENCE")
