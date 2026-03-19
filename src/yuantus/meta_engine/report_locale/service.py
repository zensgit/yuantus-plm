"""Report locale profile service layer."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.report_locale.models import PaperSize, ReportLocaleProfile


class ReportLocaleService:
    """CRUD for report locale profiles."""

    def __init__(self, session: Session):
        self.session = session

    def create_profile(
        self,
        *,
        name: str,
        lang: str = "en_US",
        fallback_lang: Optional[str] = None,
        number_format: str = "#,##0.00",
        date_format: str = "YYYY-MM-DD",
        time_format: str = "HH:mm:ss",
        timezone: str = "UTC",
        paper_size: str = PaperSize.A4.value,
        orientation: str = "portrait",
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
        logo_path: Optional[str] = None,
        report_type: Optional[str] = None,
        is_default: bool = False,
        properties: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> ReportLocaleProfile:
        if paper_size not in {e.value for e in PaperSize}:
            raise ValueError(f"Invalid paper_size: {paper_size}")
        if orientation not in {"portrait", "landscape"}:
            raise ValueError(f"Invalid orientation: {orientation}")

        profile = ReportLocaleProfile(
            id=str(uuid.uuid4()),
            name=name,
            lang=lang,
            fallback_lang=fallback_lang,
            number_format=number_format,
            date_format=date_format,
            time_format=time_format,
            timezone=timezone,
            paper_size=paper_size,
            orientation=orientation,
            header_text=header_text,
            footer_text=footer_text,
            logo_path=logo_path,
            report_type=report_type,
            is_default=is_default,
            properties=properties or {},
            created_by_id=user_id,
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def get_profile(self, profile_id: str) -> Optional[ReportLocaleProfile]:
        return self.session.get(ReportLocaleProfile, profile_id)

    def list_profiles(
        self,
        *,
        lang: Optional[str] = None,
        report_type: Optional[str] = None,
        is_default: Optional[bool] = None,
    ) -> List[ReportLocaleProfile]:
        q = self.session.query(ReportLocaleProfile)
        if lang is not None:
            q = q.filter(ReportLocaleProfile.lang == lang)
        if report_type is not None:
            q = q.filter(ReportLocaleProfile.report_type == report_type)
        if is_default is not None:
            q = q.filter(ReportLocaleProfile.is_default == is_default)
        return q.order_by(ReportLocaleProfile.name).all()

    def resolve_profile(
        self,
        *,
        lang: str,
        report_type: Optional[str] = None,
    ) -> Optional[ReportLocaleProfile]:
        """Find best-match profile: exact (lang + report_type) > lang default > global default."""
        if report_type:
            exact = (
                self.session.query(ReportLocaleProfile)
                .filter(
                    ReportLocaleProfile.lang == lang,
                    ReportLocaleProfile.report_type == report_type,
                )
                .first()
            )
            if exact:
                return exact

        lang_default = (
            self.session.query(ReportLocaleProfile)
            .filter(
                ReportLocaleProfile.lang == lang,
                ReportLocaleProfile.is_default == True,
            )
            .first()
        )
        if lang_default:
            return lang_default

        return (
            self.session.query(ReportLocaleProfile)
            .filter(ReportLocaleProfile.is_default == True)
            .first()
        )

    def update_profile(
        self, profile_id: str, **fields: Any
    ) -> Optional[ReportLocaleProfile]:
        profile = self.get_profile(profile_id)
        if not profile:
            return None
        for key, value in fields.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self.session.flush()
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        profile = self.get_profile(profile_id)
        if not profile:
            return False
        self.session.delete(profile)
        self.session.flush()
        return True

    def get_export_context(
        self,
        *,
        lang: str,
        report_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        profile = self.resolve_profile(lang=lang, report_type=report_type)
        if not profile:
            return {
                "resolved": False,
                "lang": lang,
                "report_type": report_type,
                "profile_id": None,
                "profile_name": None,
                "number_format": "#,##0.00",
                "date_format": "YYYY-MM-DD",
                "time_format": "HH:mm:ss",
                "timezone": "UTC",
                "paper_size": "a4",
                "orientation": "portrait",
                "header_text": None,
                "footer_text": None,
                "logo_path": None,
                "fallback_lang": None,
            }
        return {
            "resolved": True,
            "lang": profile.lang,
            "report_type": profile.report_type,
            "profile_id": profile.id,
            "profile_name": profile.name,
            "number_format": profile.number_format,
            "date_format": profile.date_format,
            "time_format": profile.time_format,
            "timezone": profile.timezone,
            "paper_size": profile.paper_size,
            "orientation": profile.orientation,
            "header_text": profile.header_text,
            "footer_text": profile.footer_text,
            "logo_path": profile.logo_path,
            "fallback_lang": profile.fallback_lang,
        }
