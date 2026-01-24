#!/usr/bin/env bash
# =============================================================================
# Relationship ItemType Expand Verification (Phase 2)
# Verifies: AMLQueryService expands relationship ItemTypes without RelationshipType
# =============================================================================
set -euo pipefail

PY="${PY:-.venv/bin/python}"

if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

"$PY" - <<'PY'
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yuantus.models.base import Base
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.query_service import AMLQueryService
from yuantus.meta_engine.lifecycle import models as _lifecycle_models  # noqa: F401
from yuantus.meta_engine.permission import models as _permission_models  # noqa: F401

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

part_type = ItemType(id="Part", label="Part", is_relationship=False, is_versionable=True)
rel_type = ItemType(
    id="Part Equivalent",
    label="Part Equivalent",
    is_relationship=True,
    source_item_type_id="Part",
    related_item_type_id="Part",
    is_versionable=False,
)
session.add_all([part_type, rel_type])
session.commit()

def new_item(item_type_id: str, props: dict) -> Item:
    return Item(
        id=str(uuid.uuid4()),
        item_type_id=item_type_id,
        config_id=str(uuid.uuid4()),
        generation=1,
        is_current=True,
        state="Draft",
        properties=props,
    )

part_a = new_item("Part", {"number": "EQ-A", "name": "Eq A"})
part_b = new_item("Part", {"number": "EQ-B", "name": "Eq B"})
rel = Item(
    id=str(uuid.uuid4()),
    item_type_id="Part Equivalent",
    config_id=str(uuid.uuid4()),
    generation=1,
    is_current=True,
    state="Active",
    source_id=part_a.id,
    related_id=part_b.id,
    properties={"rank": 1},
)
session.add_all([part_a, part_b, rel])
session.commit()

service = AMLQueryService(session)
result = service.get_by_id(
    item_type="Part",
    item_id=part_a.id,
    expand=["Part Equivalent"],
    depth=1,
)

if not result:
    raise SystemExit("FAIL: no result returned")

rels = result.get("Part Equivalent") or []
if not rels:
    raise SystemExit("FAIL: expand returned empty relationship list")

if rels[0].get("id") != part_b.id:
    raise SystemExit(f"FAIL: expected related {part_b.id}, got {rels}")

print("OK: expand uses ItemType relationship when RelationshipType is absent")
print("ALL CHECKS PASSED")
PY
