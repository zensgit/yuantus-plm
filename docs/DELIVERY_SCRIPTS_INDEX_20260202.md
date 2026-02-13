# Delivery Scripts Index (2026-02-02)

- backup.sh
- backup_private.sh
- backup_rotate.sh
- backup_scheduled.sh
- cleanup_private_restore.sh
- cleanup_repo_caches.sh
- migrate_tenant_db.sh
- mt_migrate.sh
- restore.sh
- restore_private.sh
- verify_backup_restore.sh
- verify_backup_rotation.sh
- verify_cleanup_restore.sh
- verify_extract_start.sh
- verify_all.sh
- verify_package.sh
- verify_permissions.sh
- verify_product_detail.sh
- verify_product_ui.sh
- verify_playwright_product_ui_summaries.sh
- verify_run_h.sh
- verify_effectivity_extended.sh
- verify_lifecycle_suspended.sh
- verify_bom_obsolete.sh
- verify_bom_weight_rollup.sh
- verify_cad_ml_quick.sh
- verify_cad_ml_metrics.sh
- verify_cad_ml_queue_smoke.sh
- verify_playwright_cad_preview_ui.sh
- collect_cad_ml_debug.sh

## Notes

- `verify_all.sh` supports `RUN_CONFIG_VARIANTS=1`, `RUN_DEDUP=1`, `START_DEDUP_STACK=1`, `RUN_OPS_S8=1`, `RUN_UI_PLAYWRIGHT=1`, and `MIGRATE_TENANT_DB=1`.
- CAD verification scripts support `USE_DOCKER_WORKER=1` to wait for jobs to be processed by a running docker-compose `worker` service (instead of running `yuantus worker --once` locally).
- `verify_playwright_product_ui_summaries.sh` requires Playwright installed in `node_modules`.
- Enable audit tests by starting the server with `YUANTUS_AUDIT_ENABLED=1`.
