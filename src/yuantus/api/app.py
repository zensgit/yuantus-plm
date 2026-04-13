from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from yuantus import __version__
from yuantus.api.middleware.auth_enforce import AuthEnforcementMiddleware
from yuantus.api.middleware.audit import AuditLogMiddleware
from yuantus.api.middleware.context import TenantOrgContextMiddleware
from yuantus.api.routers.admin import router as admin_router
from yuantus.api.routers.auth import router as auth_router
from yuantus.api.routers.cad_preview import router as cad_preview_router
from yuantus.api.routers.favicon import router as favicon_router
from yuantus.api.routers.health import router as health_router
from yuantus.api.routers.integrations import router as integrations_router
from yuantus.api.routers.jobs import router as jobs_router
from yuantus.api.routers.plugins import router as plugins_router
from yuantus.api.routers.plm_workspace import router as plm_workspace_router
from yuantus.api.routers.workbench import router as workbench_router
from yuantus.config import get_settings
from yuantus.database import init_db
from yuantus.meta_engine.web.bom_router import bom_router
from yuantus.meta_engine.web.baseline_router import baseline_router
from yuantus.meta_engine.web.box_router import box_router
from yuantus.meta_engine.web.config_router import config_router
from yuantus.meta_engine.web.cutted_parts_router import cutted_parts_router
from yuantus.meta_engine.web.cad_router import router as cad_router
from yuantus.meta_engine.web.dedup_router import dedup_router
from yuantus.meta_engine.web.document_sync_router import document_sync_router
from yuantus.meta_engine.web.eco_router import eco_router
from yuantus.meta_engine.web.approvals_router import approvals_router
from yuantus.meta_engine.web.app_router import app_router
from yuantus.meta_engine.web.change_router import change_router
from yuantus.meta_engine.web.equivalent_router import equivalent_router
from yuantus.meta_engine.web.effectivity_router import effectivity_router
from yuantus.meta_engine.web.file_router import file_router
from yuantus.meta_engine.web.esign_router import esign_router
from yuantus.meta_engine.web.permission_router import permission_router
from yuantus.meta_engine.web.product_router import product_router
from yuantus.meta_engine.web.release_readiness_router import release_readiness_router
from yuantus.meta_engine.web.release_validation_router import release_validation_router
from yuantus.meta_engine.web.release_orchestration_router import (
    release_orchestration_router,
)
from yuantus.meta_engine.web.report_router import report_router
from yuantus.meta_engine.web.query_router import query_router
from yuantus.meta_engine.web.rpc_router import rpc_router
from yuantus.meta_engine.web.router import meta_router
from yuantus.meta_engine.web.schema_router import schema_router
from yuantus.meta_engine.web.search_router import search_router
from yuantus.meta_engine.web.store_router import store_router
from yuantus.meta_engine.web.impact_router import impact_router
from yuantus.meta_engine.web.item_cockpit_router import item_cockpit_router
from yuantus.meta_engine.web.locale_router import locale_router
from yuantus.meta_engine.web.maintenance_router import maintenance_router
from yuantus.meta_engine.web.quality_router import quality_router
from yuantus.meta_engine.web.quality_analytics_router import quality_analytics_router
from yuantus.meta_engine.web.subcontracting_router import subcontracting_router
from yuantus.meta_engine.web.ui_router import ui_router
from yuantus.meta_engine.web.version_router import version_router
from yuantus.meta_engine.web.manufacturing_router import (
    mbom_router,
    routing_router,
    workcenter_router,
)
from yuantus.meta_engine.web.parallel_tasks_router import parallel_tasks_router
from yuantus.plugin_manager.runtime import load_plugins
from yuantus.security.auth.database import init_identity_db


def _run_startup(app: FastAPI) -> None:
    # Dev convenience: auto-create tables for the migrated Meta Engine kernel.
    # Production environments should use migrations instead.
    settings = get_settings()
    if settings.ENVIRONMENT == "dev":
        init_db(create_tables=True)
        init_identity_db(create_tables=True)
    from yuantus.meta_engine.services.search_indexer import (
        register_search_index_handlers,
    )

    register_search_index_handlers()
    load_plugins(app)


def _run_shutdown(app: FastAPI) -> None:
    manager = getattr(app.state, "plugin_manager", None)
    if manager and hasattr(manager, "shutdown"):
        manager.shutdown()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _run_startup(app)
    try:
        yield
    finally:
        _run_shutdown(app)


def create_app() -> FastAPI:
    app = FastAPI(title="YuantusPLM", version=__version__, lifespan=_lifespan)
    settings = get_settings()
    origins = [
        origin.strip()
        for origin in (settings.CAD_PREVIEW_CORS_ORIGINS or "").split(",")
        if origin.strip()
    ]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["GET", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=True,
        )
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(TenantOrgContextMiddleware)
    app.add_middleware(AuthEnforcementMiddleware)
    app.include_router(favicon_router)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(cad_preview_router, prefix="/api/v1")
    app.include_router(integrations_router, prefix="/api/v1")
    app.include_router(plugins_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(plm_workspace_router, prefix="/api/v1")
    app.include_router(workbench_router, prefix="/api/v1")
    app.include_router(meta_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")
    app.include_router(rpc_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(app_router, prefix="/api/v1")
    app.include_router(store_router, prefix="/api/v1")
    app.include_router(bom_router, prefix="/api/v1")
    app.include_router(box_router, prefix="/api/v1")
    app.include_router(approvals_router, prefix="/api/v1")
    app.include_router(equivalent_router, prefix="/api/v1")
    app.include_router(effectivity_router, prefix="/api/v1")
    app.include_router(baseline_router, prefix="/api/v1")
    app.include_router(config_router, prefix="/api/v1")
    app.include_router(change_router, prefix="/api/v1")  # LEGACY compat shim — sunset 2026-07-01
    app.include_router(cutted_parts_router, prefix="/api/v1")
    app.include_router(release_validation_router, prefix="/api/v1")
    app.include_router(dedup_router, prefix="/api/v1")
    app.include_router(cad_router, prefix="/api/v1")
    app.include_router(document_sync_router, prefix="/api/v1")
    app.include_router(product_router, prefix="/api/v1")
    app.include_router(permission_router, prefix="/api/v1")
    app.include_router(schema_router, prefix="/api/v1")
    app.include_router(impact_router, prefix="/api/v1")
    app.include_router(item_cockpit_router, prefix="/api/v1")
    app.include_router(locale_router, prefix="/api/v1")
    app.include_router(release_readiness_router, prefix="/api/v1")
    app.include_router(release_orchestration_router, prefix="/api/v1")
    app.include_router(ui_router, prefix="/api/v1")
    app.include_router(file_router, prefix="/api/v1")
    app.include_router(esign_router, prefix="/api/v1")
    app.include_router(version_router, prefix="/api/v1")
    app.include_router(mbom_router, prefix="/api/v1")
    app.include_router(routing_router, prefix="/api/v1")
    app.include_router(workcenter_router, prefix="/api/v1")
    app.include_router(report_router, prefix="/api/v1")
    app.include_router(eco_router, prefix="/api/v1")
    app.include_router(parallel_tasks_router, prefix="/api/v1")
    app.include_router(maintenance_router, prefix="/api/v1")
    app.include_router(quality_router, prefix="/api/v1")
    app.include_router(quality_analytics_router, prefix="/api/v1")
    app.include_router(subcontracting_router, prefix="/api/v1")

    return app


app = create_app()
