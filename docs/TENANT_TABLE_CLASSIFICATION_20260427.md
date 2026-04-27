# Tenant Table Classification (P3.4 Stop Gate)

Date: 2026-04-27

Status: **classification artifact created; sign-off pending**.

This document satisfies the written-table-classification input required before
P3.4 data migration / runtime cutover can begin. It does **not** authorize
P3.4, does not move data, and does not enable
`TENANCY_MODE=schema-per-tenant`.

## 1. Source Of Truth

The classification is derived from the current SQLAlchemy metadata helpers:

- `GLOBAL_TABLE_NAMES` in `src/yuantus/scripts/tenant_schema.py`
- `build_tenant_metadata()` in `src/yuantus/scripts/tenant_schema.py`
- `migrations_tenant/versions/t1_initial_tenant_baseline.py`

The expected invariant is:

```text
build_combined_metadata().tables == GLOBAL_TABLE_NAMES | build_tenant_metadata().tables
GLOBAL_TABLE_NAMES is disjoint from build_tenant_metadata().tables
```

Any model change that violates this partition must update this document and
the corresponding migration/test coverage before P3.4 proceeds.

## 2. Classification Rules

- Global/control-plane tables stay in the identity/global plane and must not be
  created inside a tenant schema.
- Tenant application tables are created by the tenant baseline revision inside
  each target tenant schema.
- Tenant tables may retain attribution columns such as `user_id`,
  `created_by_id`, or `assigned_user_id`, but cross-schema FK constraints to
  global tables are intentionally not created in tenant schemas.
- P3.4 export/import tooling must exclude global/control-plane tables and must
  import only the tenant application tables listed below.
- If a table is not listed below, P3.4 tooling must fail closed rather than
  guess.

## 3. Global / Control-Plane Tables (15)

- `audit_logs`
- `auth_credentials`
- `auth_org_memberships`
- `auth_organizations`
- `auth_tenant_quotas`
- `auth_tenants`
- `auth_users`
- `rbac_permissions`
- `rbac_resources`
- `rbac_role_permissions`
- `rbac_roles`
- `rbac_user_permissions`
- `rbac_user_roles`
- `rbac_users`
- `users`

## 4. Tenant Application Tables (102)

- `cad_change_logs`
- `meta_3d_overlays`
- `meta_access`
- `meta_app_licenses`
- `meta_app_registry`
- `meta_approval_categories`
- `meta_approval_request_events`
- `meta_approval_requests`
- `meta_baseline_comparisons`
- `meta_baseline_members`
- `meta_baselines`
- `meta_box_contents`
- `meta_box_items`
- `meta_breakage_incidents`
- `meta_config_option_sets`
- `meta_config_options`
- `meta_consumption_plans`
- `meta_consumption_records`
- `meta_conversion_jobs`
- `meta_cut_plans`
- `meta_cut_results`
- `meta_dashboards`
- `meta_dedup_batches`
- `meta_dedup_rules`
- `meta_eco_activity_gate_events`
- `meta_eco_activity_gates`
- `meta_eco_approvals`
- `meta_eco_bom_changes`
- `meta_eco_routing_changes`
- `meta_eco_stages`
- `meta_ecos`
- `meta_effectivities`
- `meta_electronic_signatures`
- `meta_extension_points`
- `meta_extensions`
- `meta_files`
- `meta_form_fields`
- `meta_forms`
- `meta_geometric_indices`
- `meta_grid_columns`
- `meta_grid_views`
- `meta_item_files`
- `meta_item_iterations`
- `meta_item_types`
- `meta_item_versions`
- `meta_items`
- `meta_lifecycle_maps`
- `meta_lifecycle_states`
- `meta_lifecycle_transitions`
- `meta_maintenance_categories`
- `meta_maintenance_equipment`
- `meta_maintenance_requests`
- `meta_manufacturing_boms`
- `meta_mbom_lines`
- `meta_methods`
- `meta_numbering_sequences`
- `meta_operations`
- `meta_permissions`
- `meta_plugin_configs`
- `meta_product_configurations`
- `meta_properties`
- `meta_quality_alerts`
- `meta_quality_checks`
- `meta_quality_points`
- `meta_raw_materials`
- `meta_relationship_types`
- `meta_relationships`
- `meta_remote_sites`
- `meta_report_definitions`
- `meta_report_executions`
- `meta_report_locale_profiles`
- `meta_revision_schemes`
- `meta_routings`
- `meta_saved_searches`
- `meta_signature_audit_logs`
- `meta_signature_manifests`
- `meta_signing_reasons`
- `meta_similarity_records`
- `meta_state_identity_permissions`
- `meta_store_listings`
- `meta_subcontract_approval_role_mappings`
- `meta_subcontract_order_events`
- `meta_subcontract_orders`
- `meta_sync_jobs`
- `meta_sync_records`
- `meta_sync_sites`
- `meta_translations`
- `meta_variant_rules`
- `meta_vaults`
- `meta_version_files`
- `meta_version_history`
- `meta_view_mappings`
- `meta_workcenters`
- `meta_workflow_activities`
- `meta_workflow_activity_instances`
- `meta_workflow_custom_action_rules`
- `meta_workflow_custom_action_runs`
- `meta_workflow_maps`
- `meta_workflow_processes`
- `meta_workflow_tasks`
- `meta_workflow_transitions`
- `meta_workorder_document_links`

## 5. P3.4 Stop-Gate Status

P3.4 remains blocked until every item is true:

- [ ] A non-production PostgreSQL target DSN is provisioned.
- [ ] A named pilot tenant is identified and approved.
- [ ] A backup/restore owner is named.
- [ ] A migration rehearsal window is scheduled.
- [x] P3.3.1, P3.3.2, and P3.3.3 are merged and post-merge smoke green.
- [ ] This table classification artifact is reviewed and signed off.

## 6. Sign-Off

This section is intentionally blank until the P3.4 owner signs off.

```text
Pilot tenant:
PostgreSQL rehearsal DSN:
Backup/restore owner:
Rehearsal window:
Reviewer:
Decision:
Date:
```

## 7. Non-Goals

- No source data export.
- No target data import.
- No production schema creation.
- No runtime cutover.
- No `TENANCY_MODE=schema-per-tenant` enablement.
- No changes to global identity/RBAC/audit table ownership.
