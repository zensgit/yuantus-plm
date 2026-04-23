"""Compatibility shim for the split ECO core router.

New code should import ``eco_core_router`` from ``eco_core_router.py``.
This module remains so older imports of ``yuantus.meta_engine.web.eco_router``
continue to resolve during the router decomposition transition.
"""

from yuantus.meta_engine.web.eco_core_router import eco_core_router as eco_router

__all__ = ["eco_router"]
