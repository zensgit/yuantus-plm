#!/usr/bin/env bash
# =============================================================================
# Relationship legacy usage report verification (Phase 3)
# =============================================================================
set -euo pipefail

PY="${PY:-.venv/bin/python}"

if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

PYTHONPATH=src "$PY" - <<'PY'
import json
import uuid
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.models.base import Base, WorkflowBase
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.relationship.models import RelationshipType
from yuantus.api.routers.admin import _build_relationship_legacy_usage

import_all_models()

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine, checkfirst=True)
WorkflowBase.metadata.create_all(engine, checkfirst=True)
Session = sessionmaker(bind=engine)
session = Session()

part_type = ItemType(id="Part", label="Part", is_relationship=False, is_versionable=True)
rel_item_type = ItemType(
    id="Part BOM",
    label="Part BOM",
    is_relationship=True,
    is_versionable=False,
    source_item_type_id="Part",
    related_item_type_id="Part",
)
session.add_all([part_type, rel_item_type])
session.commit()

rel_type = RelationshipType(
    id="PartBOM",
    name="Part BOM",
    label="Part BOM",
    source_item_type="Part",
    related_item_type="Part",
)
session.add(rel_type)
session.commit()

parent = Item(
    id=str(uuid.uuid4()),
    item_type_id="Part",
    config_id=str(uuid.uuid4()),
    generation=1,
    is_current=True,
    state="Draft",
    properties={"number": "P-100"},
)
child = Item(
    id=str(uuid.uuid4()),
    item_type_id="Part",
    config_id=str(uuid.uuid4()),
    generation=1,
    is_current=True,
    state="Draft",
    properties={"number": "P-200"},
)
session.add_all([parent, child])
session.commit()

legacy_rel_id = str(uuid.uuid4())
session.execute(
    text(
        "INSERT INTO meta_relationships "
        "(id, relationship_type_id, source_id, related_id, properties, sort_order, state, created_by_id) "
        "VALUES (:id, :rel_type, :source_id, :related_id, :properties, :sort_order, :state, :created_by_id)"
    ),
    {
        "id": legacy_rel_id,
        "rel_type": rel_type.id,
        "source_id": parent.id,
        "related_id": child.id,
        "properties": json.dumps({"quantity": 2}),
        "sort_order": 0,
        "state": "Active",
        "created_by_id": None,
    },
)
session.commit()

rel_item = Item(
    id=str(uuid.uuid4()),
    item_type_id="Part BOM",
    config_id=str(uuid.uuid4()),
    generation=1,
    is_current=True,
    state="Active",
    source_id=parent.id,
    related_id=child.id,
    properties={"quantity": 2},
)
session.add(rel_item)
session.commit()

entry = _build_relationship_legacy_usage(
    session,
    tenant_id="tenant-1",
    org_id="org-1",
    include_details=True,
)

assert entry.relationship_type_count == 1, entry.relationship_type_count
assert entry.relationship_row_count == 1, entry.relationship_row_count
assert entry.relationship_item_type_count == 1, entry.relationship_item_type_count
assert entry.relationship_item_count == 1, entry.relationship_item_count
assert entry.types and entry.types[0].relationship_count == 1
assert entry.types[0].relationship_item_count == 1
assert "legacy_relationship_types_present" in entry.warnings
assert "legacy_relationship_rows_present" in entry.warnings

print("ALL CHECKS PASSED")
PY
