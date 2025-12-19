"""
App Framework Models
Manage Installed Applications (Plugins/Add-ons)
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from yuantus.models.base import Base


class AppRegistry(Base):
    """
    Registry of installed applications.
    Matches the 'App Manifest' concept.
    """

    __tablename__ = "meta_app_registry"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)  # e.g. "plm.ecm"
    version = Column(String(50), nullable=False)  # e.g. "1.0.0"

    display_name = Column(String(200))  # "Engineering Change Management"
    description = Column(Text)
    author = Column(String(100))

    status = Column(
        String(20), default="Installed"
    )  # Installed, Active, Disabled, Error

    # Dependencies (JSON list of strings) - use variant for SQLite compatibility
    dependencies = Column(JSON().with_variant(JSONB, "postgresql"), default=[])

    # Installed Content (JSON logging of what was added)
    installed_content = Column(
        JSON().with_variant(JSONB, "postgresql"), default={}
    )  # {"item_types": ["ECR"], "workflows": ["Standard ECO"]}

    installed_at = Column(DateTime, default=datetime.utcnow)
    installed_by_id = Column(Integer, ForeignKey("rbac_users.id"), nullable=True)

    __table_args__ = (UniqueConstraint("name", name="uq_app_name"),)


class ExtensionPoint(Base):
    """
    Defines extension points that apps can hook into.
    """

    __tablename__ = "meta_extension_points"

    id = Column(String, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g. "item_context_menu"
    description = Column(String(500))


class Extension(Base):
    """
    An implementation of an extension point by an App.
    """

    __tablename__ = "meta_extensions"

    id = Column(String, primary_key=True)
    app_id = Column(
        String, ForeignKey("meta_app_registry.id", ondelete="CASCADE"), nullable=False
    )
    point_id = Column(
        String,
        ForeignKey("meta_extension_points.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String(100))
    handler = Column(String(200))  # "js:myApp.onAction" or "python:my_module.run"
    config = Column(
        JSON().with_variant(JSONB, "postgresql"), default={}
    )  # Specific config for the hook

    is_active = Column(Boolean, default=True)

    app = relationship("AppRegistry", backref="extensions")
    point = relationship("ExtensionPoint", backref="implementations")
