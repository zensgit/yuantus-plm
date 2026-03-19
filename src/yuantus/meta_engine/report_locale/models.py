"""
Report locale metadata models.

Stores per-report locale configuration: language, number/date formatting,
paper size, and header/footer overrides for export pipelines.
"""
from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from yuantus.models.base import Base


class PaperSize(str, enum.Enum):
    A4 = "a4"
    LETTER = "letter"
    LEGAL = "legal"
    A3 = "a3"


class ReportLocaleProfile(Base):
    """Per-report locale configuration.

    Controls language, formatting, and layout when exporting / printing
    reports such as BOM exports, quality reports, maintenance logs, etc.
    """

    __tablename__ = "meta_report_locale_profiles"

    id = Column(String, primary_key=True)
    name = Column(String(200), nullable=False)

    # Language
    lang = Column(String(10), nullable=False, default="en_US")
    fallback_lang = Column(String(10), nullable=True)

    # Number / date formatting
    number_format = Column(String(50), default="#,##0.00")
    date_format = Column(String(50), default="YYYY-MM-DD")
    time_format = Column(String(50), default="HH:mm:ss")
    timezone = Column(String(80), default="UTC")

    # Paper / layout
    paper_size = Column(String(20), default=PaperSize.A4.value)
    orientation = Column(String(20), default="portrait")  # portrait | landscape

    # Header / footer overrides
    header_text = Column(Text, nullable=True)
    footer_text = Column(Text, nullable=True)
    logo_path = Column(String, nullable=True)

    # Scope
    report_type = Column(String(120), nullable=True)  # e.g. "bom_export", "quality_report"
    is_default = Column(Boolean, default=False)

    # Extensible
    properties = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
