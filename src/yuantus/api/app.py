from __future__ import annotations

from fastapi import FastAPI

from yuantus import __version__
from yuantus.api.middleware.auth_enforce import AuthEnforcementMiddleware
from yuantus.api.middleware.audit import AuditLogMiddleware
from yuantus.api.middleware.context import TenantOrgContextMiddleware
from yuantus.api.routers.admin import router as admin_router
from yuantus.api.routers.auth import router as auth_router
from yuantus.api.routers.health import router as health_router
from yuantus.api.routers.integrations import router as integrations_router
from yuantus.api.routers.jobs import router as jobs_router
from yuantus.api.routers.plugins import router as plugins_router
from yuantus.config import get_settings
from yuantus.database import init_db
from yuantus.meta_engine.web.bom_router import bom_router
from yuantus.meta_engine.web.baseline_router import baseline_router
from yuantus.meta_engine.web.cad_router import router as cad_router
from yuantus.meta_engine.web.eco_router import eco_router
from yuantus.meta_engine.web.equivalent_router import equivalent_router
from yuantus.meta_engine.web.file_router import file_router
from yuantus.meta_engine.web.permission_router import permission_router
from yuantus.meta_engine.web.report_router import report_router
from yuantus.meta_engine.web.rpc_router import rpc_router
from yuantus.meta_engine.web.router import meta_router
from yuantus.meta_engine.web.schema_router import schema_router
from yuantus.meta_engine.web.search_router import search_router
from yuantus.meta_engine.web.ui_router import ui_router
from yuantus.meta_engine.web.version_router import version_router
from yuantus.plugin_manager.runtime import load_plugins
from yuantus.security.auth.database import init_identity_db


def create_app() -> FastAPI:
    app = FastAPI(title="YuantusPLM", version=__version__)
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(TenantOrgContextMiddleware)
    app.add_middleware(AuthEnforcementMiddleware)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    app.include_router(integrations_router, prefix="/api/v1")
    app.include_router(plugins_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(meta_router, prefix="/api/v1")
    app.include_router(rpc_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")
    app.include_router(bom_router, prefix="/api/v1")
    app.include_router(equivalent_router, prefix="/api/v1")
    app.include_router(baseline_router, prefix="/api/v1")
    app.include_router(cad_router, prefix="/api/v1")
    app.include_router(permission_router, prefix="/api/v1")
    app.include_router(schema_router, prefix="/api/v1")
    app.include_router(ui_router, prefix="/api/v1")
    app.include_router(file_router, prefix="/api/v1")
    app.include_router(version_router, prefix="/api/v1")
    app.include_router(report_router, prefix="/api/v1")
    app.include_router(eco_router, prefix="/api/v1")

    @app.on_event("startup")
    def _startup() -> None:  # pragma: no cover
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

    @app.on_event("shutdown")
    def _shutdown() -> None:  # pragma: no cover
        manager = getattr(app.state, "plugin_manager", None)
        if manager and hasattr(manager, "shutdown"):
            manager.shutdown()

    return app


app = create_app()
