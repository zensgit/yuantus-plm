"""
CAD Service
Handles CAD file attribute extraction and synchronization with Meta Engine Items.
"""

import io
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.file import FileContainer
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.meta_engine.services.validator import MetaValidator
from yuantus.exceptions.handlers import ValidationError
from yuantus.integrations.cad_connectors import (
    registry as cad_registry,
    resolve_cad_sync_key,
)
from yuantus.integrations.cad_connectors.base import normalize_cad_key
from yuantus.integrations.cad_connectors.builtin import CAD_KEY_ALIASES
from yuantus.meta_engine.services.file_service import FileService
from yuantus.integrations.cad_extractor import CadExtractorClient
from yuantus.config import get_settings
from yuantus.meta_engine.services.job_errors import JobFatalError

logger = logging.getLogger(__name__)

_WEIGHT_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?")
_MATERIAL_ALIASES: List[Tuple[str, str]] = [
    ("不锈钢304", "Stainless Steel 304"),
    ("SUS304", "Stainless Steel 304"),
    ("SS304", "Stainless Steel 304"),
    ("不锈钢316", "Stainless Steel 316"),
    ("SUS316", "Stainless Steel 316"),
    ("SS316", "Stainless Steel 316"),
    ("不锈钢", "Stainless Steel"),
    ("STAINLESS", "Stainless Steel"),
    ("碳钢", "Carbon Steel"),
    ("CARBONSTEEL", "Carbon Steel"),
    ("钢", "Steel"),
    ("STEEL", "Steel"),
    ("铝合金", "Aluminum Alloy"),
    ("ALUMINUMALLOY", "Aluminum Alloy"),
    ("ALUMINIUMALLOY", "Aluminum Alloy"),
    ("铝", "Aluminum"),
    ("ALUMINUM", "Aluminum"),
    ("ALUMINIUM", "Aluminum"),
    ("铜", "Copper"),
    ("COPPER", "Copper"),
    ("黄铜", "Brass"),
    ("BRASS", "Brass"),
    ("铸铁", "Cast Iron"),
    ("CASTIRON", "Cast Iron"),
    ("球墨铸铁", "Ductile Iron"),
    ("DUCTILEIRON", "Ductile Iron"),
    ("Q235", "Q235 Steel"),
    ("Q345", "Q345 Steel"),
]
_MATERIAL_ALIASES.sort(key=lambda item: len(item[0]), reverse=True)
_CAD_KEY_ALIAS_LOOKUP = {normalize_cad_key(k): v for k, v in CAD_KEY_ALIASES.items()}


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _apply_cad_key_aliases(attrs: Dict[str, Any]) -> Dict[str, Any]:
    if not attrs:
        return {}
    normalized: Dict[str, Any] = dict(attrs)
    key_index = {normalize_cad_key(str(k)): k for k in attrs.keys()}
    for alias_key, canonical in _CAD_KEY_ALIAS_LOOKUP.items():
        if _has_value(normalized.get(canonical)):
            continue
        raw_key = key_index.get(alias_key)
        if not raw_key:
            continue
        raw_value = normalized.get(raw_key)
        if not _has_value(raw_value):
            continue
        normalized[canonical] = raw_value
    return normalized


def _parse_weight(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return value
    match = _WEIGHT_RE.search(text)
    if not match:
        return value
    number = match.group(0).replace(",", "")
    try:
        weight = float(number)
    except ValueError:
        return value

    unit = text[match.end():].strip().lower()
    if unit:
        if unit.startswith("kg") or "公斤" in unit:
            return weight
        if unit.startswith("g") and not unit.startswith("kg"):
            return weight / 1000.0
        if unit.startswith("t") or "吨" in unit:
            return weight * 1000.0
    return weight


def _normalize_material(value: Any) -> Any:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return value
    compact = re.sub(r"\s+", "", raw)
    upper = compact.upper()
    for key, canonical in _MATERIAL_ALIASES:
        if key.isascii():
            if key in upper:
                return canonical
        else:
            if key in compact:
                return canonical
    if "304" in compact and ("不锈钢" in compact or "STAINLESS" in upper):
        return "Stainless Steel 304"
    if "316" in compact and ("不锈钢" in compact or "STAINLESS" in upper):
        return "Stainless Steel 316"
    return raw


def normalize_cad_attributes(attrs: Dict[str, Any]) -> Dict[str, Any]:
    if not attrs:
        return {}
    normalized: Dict[str, Any] = _apply_cad_key_aliases(attrs)
    for key, value in list(normalized.items()):
        if isinstance(value, str):
            normalized[key] = value.strip()

    part_number = normalized.get("part_number") or normalized.get("item_number")
    drawing_no = normalized.get("drawing_no")
    if not part_number and drawing_no:
        normalized["part_number"] = drawing_no
        part_number = drawing_no
    if part_number and not drawing_no:
        normalized["drawing_no"] = part_number

    if "material" in normalized:
        normalized["material"] = _normalize_material(normalized.get("material"))

    if "weight" in normalized:
        weight_value = _parse_weight(normalized.get("weight"))
        if weight_value is not None:
            normalized["weight"] = weight_value

    revision = normalized.get("revision")
    if isinstance(revision, str) and revision.strip():
        cleaned = re.sub(
            r"^(REV|VER|VERSION)[\\s_-]*", "", revision.strip(), flags=re.I
        )
        if cleaned and len(cleaned) == 1:
            cleaned = cleaned.upper()
        normalized["revision"] = cleaned

    return normalized


class CadService:
    def __init__(self, session: Session):
        self.session = session

    def extract_attributes(
        self,
        file_path: str,
        *,
        cad_format: Optional[str] = None,
        connector_id: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Simulates extracting attributes from a CAD file.
        In a real system, this would use libraries like ezdxf, Open Cascade, or external APIs.
        """
        logger.info(f"Simulating CAD attribute extraction from {file_path}")

        path = Path(file_path)
        connector = None
        if connector_id:
            connector = cad_registry.find_by_id(connector_id)
        if not connector and cad_format:
            connector = cad_registry.find_by_format(cad_format)
        if not connector:
            connector = cad_registry.resolve(None, path.suffix)
        if connector:
            connector_attrs = connector.extract_attributes(
                file_path, filename=path.name, content=content
            )
            if connector_attrs:
                return connector_attrs

        # Simulate different attributes based on file name for testing
        if "part_a.dwg" in file_path:
            return {
                "part_number": "PA-001",
                "description": "Assembly Part A",
                "material": "Steel",
                "revision": "A",
                "designer": "John Doe",
            }
        elif "part_b.dwg" in file_path:
            return {
                "part_number": "PB-002",
                "description": "Component Part B",
                "material": "Aluminum",
                "revision": "B",
                "weight": 1.5,
            }
        elif "failed.dwg" in file_path:
            logger.warning(f"Simulating failed extraction for {file_path}")
            raise ValueError("Simulated CAD extraction failure: file corrupt")
        else:
            return {
                "part_number": "GEN-001",
                "description": f"Generic CAD Part from {file_path}",
                "material": "Unknown",
            }

    def extract_attributes_for_file(
        self,
        file_container: FileContainer,
        *,
        file_service: Optional[FileService] = None,
        return_source: bool = False,
    ):
        file_service = file_service or FileService()
        if not file_service.file_exists(file_container.system_path):
            raise JobFatalError(
                f"Source file missing: {file_container.system_path}"
            )
        content: Optional[bytes] = None
        file_path = file_container.filename or file_container.system_path

        def _extract_filename_attrs(name: Optional[str]) -> Dict[str, Any]:
            if not name:
                return {}
            stem_name = Path(name).name
            revision_from_suffix: Optional[str] = None
            match = re.match(
                r"^(?P<stem>.+)\.(?P<ext>prt|asm)\.(?P<rev>[0-9A-Za-z]+)$",
                stem_name,
                re.I,
            )
            if match:
                stem_name = f"{match.group('stem')}.{match.group('ext')}"
                revision_from_suffix = match.group("rev")
            base = Path(stem_name).stem.strip()
            if not base:
                return {}

            base = re.sub(r"^(比较|对比|对照)[_ -]*", "", base, flags=re.I)
            base = re.split(r"\s+vs\s+", base, flags=re.I)[0].strip()

            revision = None
            rev_match = re.search(
                r"(?:[-_\s\(（])?(?P<rev>(?:rev|ver|version|v)\s*[0-9A-Za-z]+)\s*(?:\)|）)?$",
                base,
                flags=re.I,
            )
            if rev_match:
                revision = rev_match.group("rev").replace(" ", "")
                base = base[: rev_match.start()].rstrip(" -_()（）")
            elif revision_from_suffix:
                revision = revision_from_suffix

            part_number = None
            part_name = None
            part_match = re.search(r"[A-Za-z]+\d+(?:[-_][A-Za-z0-9]+)*", base)
            if part_match:
                part_number = part_match.group(0)
                remainder = base[part_match.end():].lstrip(" -_")
                if remainder:
                    part_name = remainder
            else:
                part_name = base if base else None

            attrs: Dict[str, Any] = {}
            if part_number:
                attrs["part_number"] = part_number
                attrs["drawing_no"] = part_number
            if part_name:
                attrs["part_name"] = part_name
            if revision:
                attrs["revision"] = revision
            return attrs

        def _merge_missing(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
            merged = dict(base or {})
            for key, value in (extra or {}).items():
                if key not in merged or merged[key] in (None, ""):
                    merged[key] = value
            return merged

        def _is_generic_attrs(attrs: Dict[str, Any]) -> bool:
            if not attrs:
                return True
            part_number = attrs.get("part_number")
            description = attrs.get("description")
            material = attrs.get("material")
            if (
                part_number == "GEN-001"
                and isinstance(description, str)
                and description.startswith("Generic CAD Part")
                and material == "Unknown"
            ):
                extras = {
                    key: value
                    for key, value in attrs.items()
                    if key not in {"part_number", "description", "material"}
                }
                return not extras
            return False

        local_path = file_service.get_local_path(file_container.system_path)
        if local_path and os.path.exists(local_path):
            file_path = local_path
        else:
            stream = io.BytesIO()
            file_service.download_file(file_container.system_path, stream)
            content = stream.getvalue()

        settings = get_settings()
        extractor_mode = (settings.CAD_EXTRACTOR_MODE or "optional").strip().lower()
        filename_attrs = _extract_filename_attrs(file_container.filename or file_path)
        if settings.CAD_EXTRACTOR_BASE_URL:
            def _resolve_attr(attrs: Dict[str, Any], *keys: str) -> Optional[str]:
                if not attrs:
                    return None
                lower = {str(k).lower(): v for k, v in attrs.items()}
                for key in keys:
                    value = attrs.get(key)
                    if value is None:
                        value = lower.get(key.lower())
                    if isinstance(value, str):
                        value = value.strip()
                    if value:
                        return str(value)
                return None

            def _needs_local_fallback(attrs: Dict[str, Any]) -> bool:
                if not attrs:
                    return True
                lower = {str(k).lower(): v for k, v in attrs.items()}
                for key in ("part_number", "item_number", "description", "revision"):
                    value = attrs.get(key)
                    if value is None:
                        value = lower.get(key)
                    if isinstance(value, str):
                        if value.strip():
                            continue
                    elif value is not None:
                        continue
                    return True
                return False

            temp_path: Optional[str] = None
            try:
                extractor_path = file_path
                if not (local_path and os.path.exists(local_path)):
                    suffix = Path(file_container.filename or "").suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(content or b"")
                        temp_path = tmp.name
                    extractor_path = temp_path

                client = CadExtractorClient(timeout_s=settings.CAD_EXTRACTOR_TIMEOUT_SECONDS)
                resp = client.extract_sync(
                    file_path=extractor_path,
                    filename=file_container.filename,
                    cad_format=file_container.cad_format,
                    cad_connector_id=file_container.cad_connector_id,
                )
                if isinstance(resp, dict) and resp.get("ok") is False:
                    raise JobFatalError(resp.get("error") or "CAD extractor failed")

                attrs = (
                    resp.get("attributes")
                    or resp.get("data")
                    or resp.get("result")
                    or {}
                )
                local_attrs: Optional[Dict[str, Any]] = None
                external_part = _resolve_attr(attrs, "part_number", "item_number")
                stem = Path(file_container.filename or file_path).stem if (file_container.filename or file_path) else ""
                needs_local = _needs_local_fallback(attrs)
                if external_part and stem and external_part == stem:
                    needs_local = True

                if needs_local:
                    local_attrs = self.extract_attributes(
                        file_path,
                        cad_format=file_container.cad_format,
                        connector_id=file_container.cad_connector_id,
                        content=content,
                    )

                if attrs:
                    if local_attrs and not _is_generic_attrs(local_attrs):
                        attrs = _merge_missing(attrs, local_attrs)
                        local_part = _resolve_attr(
                            local_attrs, "part_number", "item_number", "drawing_no"
                        )
                        if local_part and external_part and stem and external_part == stem:
                            attrs["part_number"] = local_part
                    if filename_attrs:
                        attrs = _merge_missing(attrs, filename_attrs)
                    attrs = normalize_cad_attributes(attrs)
                    if return_source:
                        return attrs, "external"
                    return attrs

                # External extractor returned empty attributes; try local connector fallback.
                if local_attrs and not _is_generic_attrs(local_attrs):
                    if filename_attrs:
                        local_attrs = _merge_missing(local_attrs, filename_attrs)
                    local_attrs = normalize_cad_attributes(local_attrs)
                    if return_source:
                        return local_attrs, "local"
                    return local_attrs

                if extractor_mode == "required":
                    raise JobFatalError("CAD extractor returned empty attributes")
                if filename_attrs:
                    filename_attrs = normalize_cad_attributes(filename_attrs)
                    if return_source:
                        return filename_attrs, "external"
                    return filename_attrs
                if return_source:
                    return {}, "external"
                return {}
            except Exception as exc:
                if extractor_mode == "required":
                    raise JobFatalError(f"CAD extractor failed: {exc}") from exc
                logger.warning("CAD extractor failed, fallback to local: %s", exc)
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

        attrs = self.extract_attributes(
            file_path,
            cad_format=file_container.cad_format,
            connector_id=file_container.cad_connector_id,
            content=content,
        )
        if filename_attrs:
            if _is_generic_attrs(attrs):
                attrs = dict(filename_attrs)
            else:
                attrs = _merge_missing(attrs, filename_attrs)
        attrs = normalize_cad_attributes(attrs)
        if return_source:
            return attrs, "local"
        return attrs

    def sync_attributes_to_item(
        self, item_id: str, extracted_attributes: Dict[str, Any], user_id: int
    ) -> Item:
        """
        Synchronizes extracted CAD attributes to an existing Item's properties.
        """
        item = self.session.get(Item, item_id)
        if not item:
            raise ValidationError(f"Item {item_id} not found for attribute sync.")

        item_type = self.session.get(ItemType, item.item_type_id)
        if not item_type:
            raise ValidationError(f"ItemType '{item.item_type_id}' not found for CAD sync.")

        cad_props = [prop for prop in (item_type.properties or []) if prop.is_cad_synced]
        if not cad_props:
            logger.info("No CAD-synced properties defined for ItemType %s", item_type.id)
            return item

        attributes = dict(extracted_attributes or {})
        if not attributes:
            logger.info("No extracted CAD attributes for Item %s", item_id)
            return item

        lower_attributes = {str(k).lower(): v for k, v in attributes.items()}
        updates: Dict[str, Any] = {}
        validator = MetaValidator()

        for prop in cad_props:
            cad_key = resolve_cad_sync_key(prop.name, prop.ui_options)
            if not cad_key:
                continue
            value = attributes.get(cad_key)
            if value is None:
                value = lower_attributes.get(cad_key.lower())
            if value is None:
                continue
            updates[prop.name] = validator._cast_value(prop, value)

        if not updates:
            logger.info("No matching CAD attributes for Item %s", item_id)
            return item

        current_props = dict(item.properties or {})
        current_props.update(updates)
        item.properties = current_props
        item.modified_by_id = user_id  # Update audit trail

        self.session.add(item)
        self.session.commit()  # Commit changes immediately for atomicity

        logger.info(
            "Synchronized CAD attributes for Item %s (fields=%s)",
            item_id,
            ", ".join(sorted(updates.keys())),
        )
        return item
