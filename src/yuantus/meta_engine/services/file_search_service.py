from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from yuantus.meta_engine.models.file import FileContainer


class FileSearchService:
    def __init__(self, session: Session):
        self.session = session

    def search_files(self, q: str, limit: int = 20) -> Dict[str, Any]:
        query = select(FileContainer).order_by(FileContainer.created_at.desc())
        if q:
            pattern = f"%{q}%"
            query = query.where(
                or_(
                    FileContainer.filename.ilike(pattern),
                    FileContainer.id.ilike(pattern),
                    FileContainer.cad_format.ilike(pattern),
                    cast(FileContainer.cad_properties, String).ilike(pattern),
                    cast(FileContainer.cad_attributes, String).ilike(pattern),
                )
            )

        rows = self.session.execute(query.limit(limit)).scalars().all()
        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row.id,
                    "filename": row.filename,
                    "cad_format": row.cad_format,
                    "document_type": row.document_type,
                    "document_version": row.document_version,
                    "cad_review_state": row.cad_review_state,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
            )
        return {"total": len(results), "results": results}
