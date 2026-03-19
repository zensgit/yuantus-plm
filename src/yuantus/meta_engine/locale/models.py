"""
Locale domain models – translation payload storage.

Stores translatable field values keyed by (record_type, record_id,
field_name, lang).  Mirrors Odoo's ir.translation / _get_terms approach
but uses a dedicated table instead of embedded XML.
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from yuantus.models.base import Base


class TranslationState(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"


class Translation(Base):
    """A single translatable field value.

    Each row maps (record_type, record_id, field_name, lang) → translated text.
    """

    __tablename__ = "meta_translations"
    __table_args__ = (
        UniqueConstraint(
            "record_type",
            "record_id",
            "field_name",
            "lang",
            name="uq_translation_key",
        ),
    )

    id = Column(String, primary_key=True)
    record_type = Column(String(120), nullable=False, index=True)  # e.g. "item", "quality_point"
    record_id = Column(String, nullable=False, index=True)
    field_name = Column(String(120), nullable=False)  # e.g. "name", "description"
    lang = Column(String(10), nullable=False, index=True)  # e.g. "zh_CN", "en_US", "de_DE"

    # Translation content
    source_value = Column(Text, nullable=True)  # original language value (for reference)
    translated_value = Column(Text, nullable=False)
    state = Column(String(30), default=TranslationState.DRAFT.value)

    # Context
    module = Column(String(120), nullable=True)  # origin module (e.g. "quality", "manufacturing")
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
