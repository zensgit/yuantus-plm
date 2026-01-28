# Verification - Relationship Item Migration Phase 8

Date: 2026-01-28

## Goal

Ensure legacy Relationship ORM models are still importable via the existing
`relationship.models` path, and write-block protections continue to fire.

## Command

```bash
PYTHONPATH=src python3 - <<'PY'
from yuantus.meta_engine.relationship import models as m
from yuantus.meta_engine.relationship import legacy_models as lm

print("same_class", m.Relationship is lm.Relationship, m.RelationshipType is lm.RelationshipType)

try:
    m.simulate_relationship_write_block()
except Exception as exc:
    print("blocked", type(exc).__name__, str(exc))

print("stats", m.get_relationship_write_block_stats(window_seconds=60, recent_limit=5))
PY
```

## Output

```
Blocked insert on meta_relationships (deprecated). relationship_id=sim-5314ce75-bfb6-4bc1-88d0-6958612b5829 source_id=debug-source related_id=debug-related
same_class True True
blocked RuntimeError meta_relationships is deprecated for writes; use meta_items relationship items instead.
stats {'window_seconds': 60, 'blocked': 1, 'recent': [1769591673.066184], 'last_blocked_at': 1769591673.066184}
```

## Result

PASS
