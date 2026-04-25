"""Compatibility shell for the split Document Sync routers.

Runtime `/document-sync/*` endpoints now live in focused split routers:

- `document_sync_analytics_router.py`
- `document_sync_reconciliation_router.py`
- `document_sync_replay_audit_router.py`
- `document_sync_drift_router.py`
- `document_sync_lineage_router.py`
- `document_sync_retention_router.py`
- `document_sync_freshness_router.py`
- `document_sync_core_router.py`

Keep this module as an empty registered shell until downstream imports of
`document_sync_router` are fully retired.
"""
from __future__ import annotations

from fastapi import APIRouter

document_sync_router = APIRouter(prefix="/document-sync", tags=["Document Sync"])

__all__ = ["document_sync_router"]
