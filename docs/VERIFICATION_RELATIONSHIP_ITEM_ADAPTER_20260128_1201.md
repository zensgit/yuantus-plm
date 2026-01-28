# Relationship Item Adapter Verification (2026-01-28 12:01 +0800)

## verify_relationship_type_seeding.sh
==> Legacy RelationshipType disabled (legacy=false)
REL_COUNT=0
PART_BOM_IS_REL=True
OK
==> Legacy RelationshipType enabled (legacy=true)
REL_COUNT=1
PART_BOM_IS_REL=True
OK
ALL CHECKS PASSED

## verify_relationship_itemtype_expand.sh
OK: expand uses ItemType relationship when RelationshipType is absent
ALL CHECKS PASSED

## verify_relationship_legacy_usage.sh
ALL CHECKS PASSED
