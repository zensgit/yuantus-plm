from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from fastapi.routing import APIRoute

from yuantus.api.app import create_app
from yuantus.meta_engine.web import document_sync_router as document_sync_shell_module


_EXPECTED_DOCUMENT_SYNC_ROUTE_OWNERS = {
    ("GET", "/api/v1/document-sync/overview"): "yuantus.meta_engine.web.document_sync_analytics_router",
    ("GET", "/api/v1/document-sync/sites/{site_id}/analytics"): "yuantus.meta_engine.web.document_sync_analytics_router",
    ("GET", "/api/v1/document-sync/jobs/{job_id}/conflicts"): "yuantus.meta_engine.web.document_sync_analytics_router",
    ("GET", "/api/v1/document-sync/export/overview"): "yuantus.meta_engine.web.document_sync_analytics_router",
    ("GET", "/api/v1/document-sync/export/conflicts"): "yuantus.meta_engine.web.document_sync_analytics_router",
    ("GET", "/api/v1/document-sync/reconciliation/queue"): "yuantus.meta_engine.web.document_sync_reconciliation_router",
    ("GET", "/api/v1/document-sync/reconciliation/jobs/{job_id}/summary"): "yuantus.meta_engine.web.document_sync_reconciliation_router",
    ("GET", "/api/v1/document-sync/reconciliation/sites/{site_id}/status"): "yuantus.meta_engine.web.document_sync_reconciliation_router",
    ("GET", "/api/v1/document-sync/export/reconciliation"): "yuantus.meta_engine.web.document_sync_reconciliation_router",
    ("GET", "/api/v1/document-sync/replay/overview"): "yuantus.meta_engine.web.document_sync_replay_audit_router",
    ("GET", "/api/v1/document-sync/sites/{site_id}/audit"): "yuantus.meta_engine.web.document_sync_replay_audit_router",
    ("GET", "/api/v1/document-sync/jobs/{job_id}/audit"): "yuantus.meta_engine.web.document_sync_replay_audit_router",
    ("GET", "/api/v1/document-sync/export/audit"): "yuantus.meta_engine.web.document_sync_replay_audit_router",
    ("GET", "/api/v1/document-sync/drift/overview"): "yuantus.meta_engine.web.document_sync_drift_router",
    ("GET", "/api/v1/document-sync/sites/{site_id}/snapshots"): "yuantus.meta_engine.web.document_sync_drift_router",
    ("GET", "/api/v1/document-sync/jobs/{job_id}/drift"): "yuantus.meta_engine.web.document_sync_drift_router",
    ("GET", "/api/v1/document-sync/export/drift"): "yuantus.meta_engine.web.document_sync_drift_router",
    ("GET", "/api/v1/document-sync/baseline/overview"): "yuantus.meta_engine.web.document_sync_lineage_router",
    ("GET", "/api/v1/document-sync/sites/{site_id}/lineage"): "yuantus.meta_engine.web.document_sync_lineage_router",
    ("GET", "/api/v1/document-sync/jobs/{job_id}/snapshot-lineage"): "yuantus.meta_engine.web.document_sync_lineage_router",
    ("GET", "/api/v1/document-sync/export/lineage"): "yuantus.meta_engine.web.document_sync_lineage_router",
    ("GET", "/api/v1/document-sync/checkpoints/overview"): "yuantus.meta_engine.web.document_sync_retention_router",
    ("GET", "/api/v1/document-sync/retention/summary"): "yuantus.meta_engine.web.document_sync_retention_router",
    ("GET", "/api/v1/document-sync/sites/{site_id}/checkpoints"): "yuantus.meta_engine.web.document_sync_retention_router",
    ("GET", "/api/v1/document-sync/export/retention"): "yuantus.meta_engine.web.document_sync_retention_router",
    ("GET", "/api/v1/document-sync/freshness/overview"): "yuantus.meta_engine.web.document_sync_freshness_router",
    ("GET", "/api/v1/document-sync/watermarks/summary"): "yuantus.meta_engine.web.document_sync_freshness_router",
    ("GET", "/api/v1/document-sync/sites/{site_id}/freshness"): "yuantus.meta_engine.web.document_sync_freshness_router",
    ("GET", "/api/v1/document-sync/export/watermarks"): "yuantus.meta_engine.web.document_sync_freshness_router",
    ("POST", "/api/v1/document-sync/sites"): "yuantus.meta_engine.web.document_sync_core_router",
    ("GET", "/api/v1/document-sync/sites"): "yuantus.meta_engine.web.document_sync_core_router",
    ("GET", "/api/v1/document-sync/sites/{site_id}"): "yuantus.meta_engine.web.document_sync_core_router",
    ("POST", "/api/v1/document-sync/sites/{site_id}/mirror-probe"): "yuantus.meta_engine.web.document_sync_core_router",
    ("POST", "/api/v1/document-sync/sites/{site_id}/mirror-execute"): "yuantus.meta_engine.web.document_sync_core_router",
    ("POST", "/api/v1/document-sync/jobs"): "yuantus.meta_engine.web.document_sync_core_router",
    ("GET", "/api/v1/document-sync/jobs"): "yuantus.meta_engine.web.document_sync_core_router",
    ("GET", "/api/v1/document-sync/jobs/{job_id}"): "yuantus.meta_engine.web.document_sync_core_router",
    ("GET", "/api/v1/document-sync/jobs/{job_id}/summary"): "yuantus.meta_engine.web.document_sync_core_router",
}

_ROUTER_REGISTRATION_ORDER = [
    "document_sync_analytics_router",
    "document_sync_reconciliation_router",
    "document_sync_replay_audit_router",
    "document_sync_drift_router",
    "document_sync_lineage_router",
    "document_sync_retention_router",
    "document_sync_freshness_router",
    "document_sync_core_router",
]


def _is_document_sync_route(path: str) -> bool:
    return path == "/api/v1/document-sync" or path.startswith("/api/v1/document-sync/")


def _app_document_sync_routes() -> dict[tuple[str, str], str]:
    routes: dict[tuple[str, str], str] = {}
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_document_sync_route(route.path):
            continue
        for method in route.methods or set():
            if method == "HEAD":
                continue
            routes[(method, route.path)] = route.endpoint.__module__
    return routes


def test_all_document_sync_routes_have_explicit_split_router_owner() -> None:
    assert _app_document_sync_routes() == _EXPECTED_DOCUMENT_SYNC_ROUTE_OWNERS


def test_all_document_sync_routes_are_registered_exactly_once() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not _is_document_sync_route(route.path):
            continue
        for method in route.methods or set():
            if method != "HEAD":
                counts[(method, route.path)] += 1

    assert set(counts) == set(_EXPECTED_DOCUMENT_SYNC_ROUTE_OWNERS)
    assert all(count == 1 for count in counts.values())


def test_legacy_document_sync_router_module_is_shell_only() -> None:
    text = Path(document_sync_shell_module.__file__).read_text(encoding="utf-8")
    assert re.findall(r"@document_sync_router\.(get|post|delete|put|patch)\(", text) == []
    assert "document_sync_router = APIRouter" in text


def test_app_registers_document_sync_routers_in_decomposition_order() -> None:
    app_py = Path(__file__).resolve().parents[4] / "src" / "yuantus" / "api" / "app.py"
    text = app_py.read_text(encoding="utf-8")
    positions = [
        text.find(f"app.include_router({router_name}")
        for router_name in _ROUTER_REGISTRATION_ORDER
    ]

    assert all(position != -1 for position in positions)
    assert positions == sorted(positions)
    assert "app.include_router(document_sync_router," not in text, (
        "Legacy document_sync_router shell must not be registered after Phase 1 P1.10"
    )
    assert "from yuantus.meta_engine.web.document_sync_router import" not in text, (
        "Legacy document_sync_router shell must not be imported by app.py after Phase 1 P1.10"
    )
