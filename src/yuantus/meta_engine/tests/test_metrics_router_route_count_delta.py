from __future__ import annotations

from yuantus.api.app import create_app


EXPECTED_TOTAL_ROUTES = 672


def test_metrics_router_brings_total_routes_to_expected_count() -> None:
    """Phase 2 P2.2 contract: registering metrics_router moves the total
    route count from 671 (post-Phase-1) to 672. If a future change adds a
    second route in this PR's scope, this test fails and forces a
    conversation about scope creep."""
    app = create_app()
    assert len(app.routes) == EXPECTED_TOTAL_ROUTES, (
        f"expected {EXPECTED_TOTAL_ROUTES} total routes after P2.2, "
        f"got {len(app.routes)}"
    )


def test_metrics_endpoint_is_the_single_route_added_by_metrics_router() -> None:
    app = create_app()
    metrics_owned = [
        r
        for r in app.routes
        if getattr(r, "endpoint", None) is not None
        and getattr(r.endpoint, "__module__", "") == "yuantus.api.routers.metrics"
    ]
    assert len(metrics_owned) == 1, (
        f"metrics_router must own exactly 1 route in P2.2 scope; "
        f"found {len(metrics_owned)}"
    )
    assert metrics_owned[0].path == "/api/v1/metrics"
