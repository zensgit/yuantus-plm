# Relationship Item Phase 3 Verification (2026-01-28 14:32 +0800)

## Seed platform admin
Seeded identity: tenant=platform, org=platform, user=platform-admin (9001)

## Login platform admin
platform_token_present=yes

## Relationship write blocks (initial)
{
    "window_seconds": 86400,
    "blocked": 0,
    "recent": [],
    "last_blocked_at": null,
    "warn_threshold": 1,
    "warn": false
}

## Relationship write blocks simulate
{
    "window_seconds": 86400,
    "blocked": 1,
    "recent": [
        1769581971.4492135
    ],
    "last_blocked_at": 1769581971.4492135,
    "warn_threshold": 1,
    "warn": true
}

## Relationship write blocks (after)
{
    "window_seconds": 86400,
    "blocked": 1,
    "recent": [
        1769581971.4492135
    ],
    "last_blocked_at": 1769581971.4492135,
    "warn_threshold": 1,
    "warn": true
}

## Legacy usage report (admin)
admin_token_present=yes
{
    "items": [
        {
            "tenant_id": "tenant-1",
            "org_id": "org-1",
            "relationship_type_count": 0,
            "relationship_row_count": 0,
            "relationship_item_type_count": 5,
            "relationship_item_count": 733,
            "meta_relationships_missing": false,
            "meta_relationship_types_missing": false,
            "legacy": true,
            "deprecation_note": "Legacy RelationshipType/model is deprecated; use ItemType relationships",
            "types": [],
            "warnings": [
                "relationship_items_without_relationship_types"
            ]
        }
    ],
    "total": 1
}

## Legacy write blocked (ORM insert)
BLOCKED: RuntimeError meta_relationships is deprecated for writes; use meta_items relationship items instead.
