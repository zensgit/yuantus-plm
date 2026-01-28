# Verification - Relationship Item Migration Phase 9

Date: 2026-01-28

## Goal

Confirm internal modules import legacy relationship models directly.

## Command

```bash
PYTHONPATH=src python3 - <<'PY'
from yuantus.seeder.meta import schemas
from yuantus.meta_engine.relationship import legacy_models as lm
print("seeder_rel_type_module", schemas.RelationshipType.__module__)
print("same_class", schemas.RelationshipType is lm.RelationshipType)

from yuantus.api.routers import admin
print("admin_block_fn_module", admin.get_relationship_write_block_stats.__module__)
PY
```

## Output

```
seeder_rel_type_module yuantus.meta_engine.relationship.legacy_models
same_class True
admin_block_fn_module yuantus.meta_engine.relationship.legacy_models
```

## Result

PASS
