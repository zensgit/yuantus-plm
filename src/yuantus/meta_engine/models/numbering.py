"""
Numbering models.
Stores per-scope counters for auto-generated item numbers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from yuantus.models.base import Base


class NumberingSequence(Base):
    __tablename__ = "meta_numbering_sequences"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    item_type_id = Column(String(120), nullable=False, index=True)
    tenant_id = Column(String(120), nullable=False, default="default", index=True)
    org_id = Column(String(120), nullable=False, default="default", index=True)
    prefix = Column(String(120), nullable=False)
    width = Column(Integer, nullable=False, default=6)
    last_value = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "item_type_id",
            "tenant_id",
            "org_id",
            "prefix",
            name="uq_numbering_sequence_scope",
        ),
    )
