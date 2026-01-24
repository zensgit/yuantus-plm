#!/usr/bin/env bash
# =============================================================================
# RelationshipType Seeding Verification (Phase 3)
# Verifies: legacy RelationshipType seeding is optional and off by default.
# =============================================================================
set -euo pipefail

PY="${PY:-.venv/bin/python}"

if [[ ! -x "$PY" ]]; then
  echo "Missing Python at $PY (set PY=...)" >&2
  exit 2
fi

run_case() {
  local legacy_flag="$1"
  local expect_rel="$2"
  local label="$3"

  echo "==> $label (legacy=$legacy_flag)"
  YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED="$legacy_flag" \
  EXPECT_REL_COUNT="$expect_rel" \
  PYTHONPATH=src \
    "$PY" - <<'PY'
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import types

from yuantus.meta_engine.bootstrap import import_all_models
from yuantus.models.base import Base, WorkflowBase
from yuantus.meta_engine.relationship.models import RelationshipType
from yuantus.meta_engine.models.meta_schema import ItemType

class _DummyFaker:
    def __init__(self, *args, **kwargs):
        pass

sys.modules["faker"] = types.SimpleNamespace(Faker=_DummyFaker)

from yuantus.seeder.meta.schemas import MetaSchemaSeeder

import_all_models()
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine, checkfirst=True)
WorkflowBase.metadata.create_all(engine, checkfirst=True)
Session = sessionmaker(bind=engine)
session = Session()

MetaSchemaSeeder(session).run()
session.commit()

rel_count = session.query(RelationshipType).count()
item_rel = session.query(ItemType).filter_by(id="Part BOM").first()
print(f"REL_COUNT={rel_count}")
print(f"PART_BOM_IS_REL={getattr(item_rel, 'is_relationship', None)}")

expect_rel = os.environ.get("EXPECT_REL_COUNT", "0")
if expect_rel == "0":
    if rel_count != 0:
        raise SystemExit(f"FAIL: expected 0 RelationshipType rows, got {rel_count}")
else:
    if rel_count < 1:
        raise SystemExit("FAIL: expected RelationshipType rows")

if not item_rel or not item_rel.is_relationship:
    raise SystemExit("FAIL: Part BOM ItemType missing or not relationship")

print("OK")
PY
}

run_case "false" "0" "Legacy RelationshipType disabled"
run_case "true" "1" "Legacy RelationshipType enabled"

echo "ALL CHECKS PASSED"
