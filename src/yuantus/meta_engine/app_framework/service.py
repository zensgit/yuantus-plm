"""
App Framework Service
Manage installation, uninstallation, and extension registry.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from yuantus.meta_engine.app_framework.models import (
    AppRegistry,
    Extension,
    ExtensionPoint,
)


class AppError(Exception):
    pass


class AppService:
    def __init__(self, session: Session):
        self.session = session

    def register_app(self, manifest: Dict[str, Any], installer_id: int) -> AppRegistry:
        """
        Register a new application from its manifest.
        manifest example:
        {
            "name": "plm.ecm",
            "version": "1.0.0",
            "display_name": "Change Management",
            "extensions": [
                {"point": "menu", "name": "ECM Menu", "handler": "js:...", "config": {...}}
            ]
        }
        """
        name = manifest.get("name")
        version = manifest.get("version")

        # Check if already installed
        existing = self.session.query(AppRegistry).filter_by(name=name).first()
        if existing:
            # Upgrade logic could go here
            if existing.version == version:
                return existing
            else:
                existing.version = version
                existing.status = "Upgraded"
                return existing

        app = AppRegistry(
            id=str(uuid.uuid4()),
            name=name,
            version=version,
            display_name=manifest.get("display_name", name),
            description=manifest.get("description"),
            author=manifest.get("author"),
            dependencies=manifest.get("dependencies", []),
            status="Installed",
            installed_at=datetime.utcnow(),
            installed_by_id=installer_id,
        )
        self.session.add(app)
        self.session.flush()  # Get ID

        # Process Extensions
        extensions = manifest.get("extensions", [])
        for ext_def in extensions:
            point_name = ext_def.get("point")
            point = self.get_extension_point(point_name)
            if not point:
                # Decide if strictly fail or skip.
                # For robustness, we might auto-create or skip. Skipping for now.
                print(f"Warning: Extension point {point_name} not found for app {name}")
                continue

            ext = Extension(
                id=str(uuid.uuid4()),
                app_id=app.id,
                point_id=point.id,
                name=ext_def.get("name"),
                handler=ext_def.get("handler"),
                config=ext_def.get("config", {}),
                is_active=True,
            )
            self.session.add(ext)

        return app

    def get_extension_point(self, name: str) -> Optional[ExtensionPoint]:
        return self.session.query(ExtensionPoint).filter_by(name=name).first()

    def create_extension_point(
        self, name: str, description: str = ""
    ) -> ExtensionPoint:
        ep = ExtensionPoint(id=str(uuid.uuid4()), name=name, description=description)
        self.session.add(ep)
        return ep

    def get_extensions_for_point(self, point_name: str) -> List[Extension]:
        """
        Get all active extensions for a specific point name.
        """
        return (
            self.session.query(Extension)
            .join(ExtensionPoint, Extension.point_id == ExtensionPoint.id)
            .join(AppRegistry, Extension.app_id == AppRegistry.id)
            .filter(ExtensionPoint.name == point_name)
            .filter(Extension.is_active.is_(True))
            .filter(AppRegistry.status.in_(["Installed", "Active", "Upgraded"]))
            .all()
        )

    def uninstall_app(self, app_name: str):
        app = self.session.query(AppRegistry).filter_by(name=app_name).first()
        if not app:
            raise AppError("App not found")

        # Cascading delete handles extensions
        self.session.delete(app)
