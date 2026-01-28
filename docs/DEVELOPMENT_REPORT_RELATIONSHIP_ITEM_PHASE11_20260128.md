# Relationship Item Migration - Phase 11 (Docs Cleanup)

Date: 2026-01-28

## Goal

Remove or clarify any remaining documentation that suggests `RelationshipType`
usage is a normal path. Ensure docs point users to ItemType relationships.

## Summary of Changes

- Updated seeder documentation to mark `RelationshipType` as legacy-only and
  clarify that new relationships use `ItemType.is_relationship` + `Item`.

## Files Changed

- `src/yuantus/seeder/README.md`
  - Clarified schema layer description and legacy seeding note.

## Risk

None (documentation only).
