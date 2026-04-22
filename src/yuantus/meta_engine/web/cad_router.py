from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/cad", tags=["CAD"])

"""
CAD legacy aggregate router.

Domain-specific CAD routes now live in split routers:
- cad_import_router
- cad_checkin_router
- cad_view_state_router
- cad_history_router
- cad_file_data_router
- cad_mesh_stats_router
- cad_properties_router
- cad_review_router
- cad_diff_router
- cad_connectors_router
- cad_sync_template_router
- cad_backend_profile_router
"""
