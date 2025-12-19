from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Workflow tables are optional; keep a dedicated base to avoid polluting the core metadata.
WorkflowBase = declarative_base()

