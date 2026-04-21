"""Locale / translation service layer."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from yuantus.meta_engine.locale.models import Translation, TranslationState


def _normalize_lang_chain(
    lang: Optional[str],
    fallback_langs: Optional[List[str]] = None,
) -> List[str]:
    result: List[str] = []
    raw_values: List[Any] = []
    if lang is not None:
        raw_values.append(lang)
    raw_values.extend(fallback_langs or [])

    for raw in raw_values:
        for part in str(raw or "").split(","):
            value = part.strip()
            if value and value not in result:
                result.append(value)
    return result


def _localized_maps(
    properties: Dict[str, Any],
    field_name: str,
) -> List[tuple[str, Dict[str, Any]]]:
    candidates: List[tuple[str, Any]] = [
        ("properties_map", properties.get(field_name)),
        ("properties_i18n", properties.get(f"{field_name}_i18n")),
        ("properties_translations", properties.get(f"{field_name}_translations")),
    ]

    for bucket_name in ("i18n", "translations"):
        bucket = properties.get(bucket_name)
        if isinstance(bucket, dict):
            candidates.append((f"properties_{bucket_name}", bucket.get(field_name)))

    result: List[tuple[str, Dict[str, Any]]] = []
    for source, value in candidates:
        if isinstance(value, dict):
            result.append((source, value))
    return result


def resolve_localized_property(
    properties: Optional[Dict[str, Any]],
    field_name: str,
    *,
    lang: str,
    fallback_langs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    props = properties or {}
    chain: List[Dict[str, Any]] = []
    lang_chain = _normalize_lang_chain(lang, fallback_langs)

    for source, translations in _localized_maps(props, field_name):
        for try_lang in lang_chain:
            value = translations.get(try_lang)
            exists = value is not None and str(value).strip() != ""
            chain.append(
                {
                    "lang": try_lang,
                    "source": source,
                    "exists": exists,
                    "value": value if exists else None,
                }
            )
            if exists:
                return {
                    "resolved": True,
                    "value": value,
                    "resolved_from_lang": try_lang,
                    "source": source,
                    "chain": chain,
                }

    scalar = props.get(field_name)
    if scalar is not None and not isinstance(scalar, dict) and str(scalar).strip() != "":
        return {
            "resolved": True,
            "value": scalar,
            "resolved_from_lang": None,
            "source": "properties_scalar",
            "chain": chain,
        }

    return {
        "resolved": False,
        "value": None,
        "resolved_from_lang": None,
        "source": None,
        "chain": chain,
    }


class LocaleService:
    """CRUD for translation payloads."""

    def __init__(self, session: Session):
        self.session = session

    def upsert_translation(
        self,
        *,
        record_type: str,
        record_id: str,
        field_name: str,
        lang: str,
        translated_value: str,
        source_value: Optional[str] = None,
        state: str = TranslationState.DRAFT.value,
        module: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Translation:
        if state not in {e.value for e in TranslationState}:
            raise ValueError(f"Invalid state: {state}")

        existing = (
            self.session.query(Translation)
            .filter(
                Translation.record_type == record_type,
                Translation.record_id == record_id,
                Translation.field_name == field_name,
                Translation.lang == lang,
            )
            .first()
        )

        if existing:
            existing.translated_value = translated_value
            if source_value is not None:
                existing.source_value = source_value
            existing.state = state
            if module is not None:
                existing.module = module
            self.session.flush()
            return existing

        t = Translation(
            id=str(uuid.uuid4()),
            record_type=record_type,
            record_id=record_id,
            field_name=field_name,
            lang=lang,
            translated_value=translated_value,
            source_value=source_value,
            state=state,
            module=module,
            created_by_id=user_id,
        )
        self.session.add(t)
        self.session.flush()
        return t

    def get_translation(
        self,
        *,
        record_type: str,
        record_id: str,
        field_name: str,
        lang: str,
    ) -> Optional[Translation]:
        return (
            self.session.query(Translation)
            .filter(
                Translation.record_type == record_type,
                Translation.record_id == record_id,
                Translation.field_name == field_name,
                Translation.lang == lang,
            )
            .first()
        )

    def get_translations_for_record(
        self,
        *,
        record_type: str,
        record_id: str,
        lang: Optional[str] = None,
    ) -> List[Translation]:
        q = self.session.query(Translation).filter(
            Translation.record_type == record_type,
            Translation.record_id == record_id,
        )
        if lang is not None:
            q = q.filter(Translation.lang == lang)
        return q.order_by(Translation.field_name, Translation.lang).all()

    def get_translations_by_lang(
        self,
        *,
        lang: str,
        record_type: Optional[str] = None,
        module: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[Translation]:
        q = self.session.query(Translation).filter(Translation.lang == lang)
        if record_type is not None:
            q = q.filter(Translation.record_type == record_type)
        if module is not None:
            q = q.filter(Translation.module == module)
        if state is not None:
            q = q.filter(Translation.state == state)
        return q.order_by(Translation.record_type, Translation.record_id).all()

    def bulk_upsert(
        self,
        translations: List[Dict[str, Any]],
        *,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        created = 0
        updated = 0
        errors: List[str] = []
        for i, entry in enumerate(translations):
            try:
                existing = self.get_translation(
                    record_type=entry["record_type"],
                    record_id=entry["record_id"],
                    field_name=entry["field_name"],
                    lang=entry["lang"],
                )
                self.upsert_translation(
                    record_type=entry["record_type"],
                    record_id=entry["record_id"],
                    field_name=entry["field_name"],
                    lang=entry["lang"],
                    translated_value=entry["translated_value"],
                    source_value=entry.get("source_value"),
                    state=entry.get("state", TranslationState.DRAFT.value),
                    module=entry.get("module"),
                    user_id=user_id,
                )
                if existing:
                    updated += 1
                else:
                    created += 1
            except (KeyError, ValueError) as exc:
                errors.append(f"Row {i}: {exc}")

        return {"created": created, "updated": updated, "errors": errors}

    def delete_translation(
        self,
        *,
        record_type: str,
        record_id: str,
        field_name: str,
        lang: str,
    ) -> bool:
        t = self.get_translation(
            record_type=record_type,
            record_id=record_id,
            field_name=field_name,
            lang=lang,
        )
        if not t:
            return False
        self.session.delete(t)
        self.session.flush()
        return True

    def resolve_translation(
        self,
        *,
        record_type: str,
        record_id: str,
        field_name: str,
        lang: str,
        fallback_langs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        chain: List[Dict[str, Any]] = []
        langs_to_try = [lang] + (fallback_langs or [])

        for try_lang in langs_to_try:
            translation = self.get_translation(
                record_type=record_type,
                record_id=record_id,
                field_name=field_name,
                lang=try_lang,
            )
            chain.append(
                {
                    "lang": try_lang,
                    "exists": translation is not None,
                    "value": translation.translated_value if translation else None,
                    "source_value": translation.source_value if translation else None,
                    "state": translation.state if translation else None,
                }
            )
            if translation is not None:
                return {
                    "resolved": True,
                    "value": translation.translated_value,
                    "resolved_from_lang": try_lang,
                    "chain": chain,
                }

        return {
            "resolved": False,
            "value": None,
            "resolved_from_lang": None,
            "chain": chain,
        }

    def resolve_translations_batch(
        self,
        *,
        record_type: str,
        record_id: str,
        fields: List[str],
        lang: str,
        fallback_langs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        resolved: List[Dict[str, Any]] = []
        missing: List[str] = []
        fallbacks_used: List[str] = []

        for field_name in fields:
            result = self.resolve_translation(
                record_type=record_type,
                record_id=record_id,
                field_name=field_name,
                lang=lang,
                fallback_langs=fallback_langs,
            )
            if result["resolved"]:
                resolved.append(
                    {
                        "field": field_name,
                        "lang": result["resolved_from_lang"],
                        "value": result["value"],
                    }
                )
                resolved_lang = result["resolved_from_lang"]
                if resolved_lang != lang and resolved_lang not in fallbacks_used:
                    fallbacks_used.append(resolved_lang)
            else:
                missing.append(field_name)

        return {
            "resolved": resolved,
            "missing": missing,
            "fallbacks_used": fallbacks_used,
        }

    def resolve_item_localized_fields(
        self,
        item: Any,
        *,
        fields: List[str],
        lang: str,
        fallback_langs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        record_id = str(getattr(item, "id"))
        properties = getattr(item, "properties", None) or {}
        resolved: List[Dict[str, Any]] = []
        missing: List[str] = []
        fallbacks_used: List[str] = []

        for field_name in fields:
            translation = self.resolve_translation(
                record_type="item",
                record_id=record_id,
                field_name=field_name,
                lang=lang,
                fallback_langs=fallback_langs,
            )
            if translation["resolved"]:
                resolved_lang = translation["resolved_from_lang"]
                resolved.append(
                    {
                        "field": field_name,
                        "lang": resolved_lang,
                        "value": translation["value"],
                        "source": "translation",
                        "chain": translation["chain"],
                    }
                )
                if resolved_lang != lang and resolved_lang not in fallbacks_used:
                    fallbacks_used.append(resolved_lang)
                continue

            prop_result = resolve_localized_property(
                properties,
                field_name,
                lang=lang,
                fallback_langs=fallback_langs,
            )
            if prop_result["resolved"]:
                resolved_lang = prop_result["resolved_from_lang"]
                resolved.append(
                    {
                        "field": field_name,
                        "lang": resolved_lang,
                        "value": prop_result["value"],
                        "source": prop_result["source"],
                        "chain": prop_result["chain"],
                    }
                )
                if resolved_lang and resolved_lang != lang and resolved_lang not in fallbacks_used:
                    fallbacks_used.append(resolved_lang)
            else:
                missing.append(field_name)

        return {
            "record_type": "item",
            "record_id": record_id,
            "lang": lang,
            "fallback_langs": fallback_langs or [],
            "resolved": resolved,
            "missing": missing,
            "fallbacks_used": fallbacks_used,
        }

    def fallback_preview(
        self,
        *,
        record_type: str,
        record_id: str,
        field_name: str,
        lang: str,
        fallback_langs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        result = self.resolve_translation(
            record_type=record_type,
            record_id=record_id,
            field_name=field_name,
            lang=lang,
            fallback_langs=fallback_langs,
        )
        return {
            "request": {
                "record_type": record_type,
                "record_id": record_id,
                "field_name": field_name,
                "primary_lang": lang,
                "fallback_chain": fallback_langs or [],
            },
            "resolution_chain": result["chain"],
            "resolved_value": result["value"],
            "resolved_from_lang": result["resolved_from_lang"],
        }
