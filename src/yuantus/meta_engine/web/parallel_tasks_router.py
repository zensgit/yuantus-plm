from __future__ import annotations

from fastapi import APIRouter

# Compatibility import surface retained after router decomposition R8.
# Business endpoints now live in dedicated split routers.
parallel_tasks_router = APIRouter(tags=["ParallelTasks"])
