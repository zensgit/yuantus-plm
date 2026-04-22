from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from yuantus.meta_engine.models.cad_audit import CadChangeLog
from yuantus.meta_engine.models.file import FileContainer


def log_cad_change(
    db: Session,
    file_container: FileContainer,
    action: str,
    payload: Dict[str, Any],
    user,
) -> None:
    entry = CadChangeLog(
        file_id=file_container.id,
        action=action,
        payload=payload,
        tenant_id=user.tenant_id,
        org_id=user.org_id,
        user_id=user.id,
    )
    db.add(entry)
