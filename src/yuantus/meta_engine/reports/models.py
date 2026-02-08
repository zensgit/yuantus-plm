"""
Report and advanced search models.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from yuantus.models.base import Base


class ReportType(str, enum.Enum):
    TABLE = "table"
    CHART = "chart"
    PIVOT = "pivot"
    DASHBOARD = "dashboard"
    CROSSTAB = "crosstab"


class ChartType(str, enum.Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    TREEMAP = "treemap"
    GAUGE = "gauge"


class SavedSearch(Base):
    __tablename__ = "meta_saved_searches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    owner_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    is_public = Column(Boolean, default=False)

    item_type_id = Column(String, ForeignKey("meta_item_types.id"), nullable=True)

    criteria = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    display_columns = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    page_size = Column(Integer, default=25)

    use_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ReportDefinition(Base):
    __tablename__ = "meta_report_definitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    code = Column(String, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)

    report_type = Column(String, default=ReportType.TABLE.value)

    data_source = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    layout = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    parameters = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    owner_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    is_public = Column(Boolean, default=False)
    allowed_roles = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ReportExecution(Base):
    __tablename__ = "meta_report_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    report_id = Column(
        String,
        ForeignKey("meta_report_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    parameters_used = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    status = Column(String, default="running")
    error_message = Column(Text, nullable=True)

    row_count = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    export_format = Column(String, nullable=True)
    export_path = Column(String, nullable=True)

    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    executed_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Dashboard(Base):
    __tablename__ = "meta_dashboards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    layout = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    widgets = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    auto_refresh = Column(Boolean, default=False)
    refresh_interval = Column(Integer, default=300)

    owner_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)
