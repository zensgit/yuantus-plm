# Verification - Relationship Item Migration Phase 11

Date: 2026-01-28

## Goal

Confirm seeder documentation reflects legacy-only RelationshipType guidance.

## Command

```bash
rg -n "legacy RelationshipTypes optional|Legacy RelationshipTypes" src/yuantus/seeder/README.md
```

## Output

```
62:| 100-199 | Schema | ItemTypes (legacy RelationshipTypes optional) |
70:- **Legacy RelationshipTypes**: Deprecated. Seed only when required by legacy integrations via `YUANTUS_RELATIONSHIP_TYPE_LEGACY_SEED_ENABLED=true`; new relationships must use `ItemType.is_relationship` + `Item` relations.
```

## Result

PASS
