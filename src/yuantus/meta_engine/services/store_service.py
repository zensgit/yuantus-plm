"""
App Store Service
Manages connection to the PLM App Registry, downloading, and installing apps.
"""

from typing import List, Dict, Any
import requests
import os
import uuid
from sqlalchemy.orm import Session
from yuantus.meta_engine.app_framework.models import AppInstall

REGISTRY_URL = os.getenv("PLM_REGISTRY_URL", "https://registry.plm.example.com/api")


class AppStoreService:
    def __init__(self, session: Session):
        self.session = session

    def search_apps(self, query: str = "") -> List[Dict[str, Any]]:
        """
        Search for apps in the remote registry.
        For MVP simulation, return hardcoded list if registry not reachable.
        """
        try:
            resp = requests.get(
                f"{REGISTRY_URL}/search", params={"q": query}, timeout=2
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass

        # Simulation Mode
        apps = [
            {
                "id": "com.plm.pdf_viewer",
                "name": "PDF Viewer",
                "version": "1.0.0",
                "description": "Embedded PDF viewer for Documents.",
                "price": 0,
                "icon": "📝",
            },
            {
                "id": "com.plm.advanced_analytics",
                "name": "Advanced Analytics",
                "version": "2.1.0",
                "description": "Power BI integration and dashboards.",
                "price": 299,
                "icon": "📊",
            },
            {
                "id": "com.plm.slack_bot",
                "name": "Slack Integration",
                "version": "1.0.1",
                "description": "Notify Slack channel on Workflow events.",
                "price": 0,
                "icon": "💬",
            },
        ]

        if query:
            apps = [a for a in apps if query.lower() in a["name"].lower()]

        # Enrich with installed status
        installed = {app.app_id: app for app in self.session.query(AppInstall).all()}

        for app in apps:
            if app["id"] in installed:
                app["status"] = "installed"
                app["installed_version"] = installed[app["id"]].installed_version
            else:
                app["status"] = "available"

        return apps

    def install_app(self, app_id: str, version: str) -> bool:
        """
        Simulate app installation.
        In real life: Download ZIP, extract to extensions dir, run migrations.
        """
        # Check if already installed
        existing = self.session.query(AppInstall).filter_by(app_id=app_id).first()
        if existing:
            return True  # Already done

        print(f"Installing {app_id} v{version}...")

        # 1. Download (Simulated)
        # 2. Extract
        # 3. Register

        install_rec = AppInstall(
            id=str(uuid.uuid4()),
            app_id=app_id,
            installed_version=version,
            status="active",
            config={},
        )
        self.session.add(install_rec)
        self.session.commit()

        return True

    def uninstall_app(self, app_id: str) -> bool:
        rec = self.session.query(AppInstall).filter_by(app_id=app_id).first()
        if rec:
            self.session.delete(rec)
            self.session.commit()
        return True
