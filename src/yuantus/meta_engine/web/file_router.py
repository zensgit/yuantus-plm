"""
Legacy File Management router shell.

Runtime `/file/*` endpoints now live in focused split routers:

- `file_conversion_router.py`
- `file_viewer_router.py`
- `file_storage_router.py`
- `file_attachment_router.py`
- `file_metadata_router.py`

Keep this module as an empty compatibility import until downstream references to
`file_router` are fully retired.
"""

from __future__ import annotations

from fastapi import APIRouter


file_router = APIRouter(prefix="/file", tags=["File Management"])

__all__ = ["file_router"]
