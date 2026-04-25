from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from fastapi import HTTPException
from sqlalchemy.orm import Session


@contextmanager
def transactional_write(db: Session) -> Iterator[None]:
    try:
        yield
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
