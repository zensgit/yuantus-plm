from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Sequence


def normalize_cad_format(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().upper()
    return normalized or None


def normalize_cad_key(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = value.strip().upper()
    if not normalized:
        return ""
    normalized = (
        normalized.replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )
    normalized = normalized.replace("(", "").replace(")", "")
    normalized = normalized.replace("（", "").replace("）", "")
    normalized = re.sub(r"_+", "_", normalized)
    return normalized


def resolve_cad_sync_key(name: str, ui_options: object) -> str:
    options: Dict[str, object] = {}
    if isinstance(ui_options, dict):
        options = ui_options
    elif isinstance(ui_options, str):
        try:
            parsed = json.loads(ui_options)
            if isinstance(parsed, dict):
                options = parsed
        except json.JSONDecodeError:
            options = {}
    for key in ("cad_key", "cad_attribute", "cad_sync_key"):
        value = options.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return name


@dataclass(frozen=True)
class CadConnectorInfo:
    id: str
    label: str
    cad_format: str
    document_type: str
    extensions: Sequence[str] = field(default_factory=tuple)
    aliases: Sequence[str] = field(default_factory=tuple)
    priority: int = 0
    description: Optional[str] = None
    signature_tokens: Sequence[str] = field(default_factory=tuple)

    def normalized_formats(self) -> set[str]:
        formats = {normalize_cad_format(self.cad_format)}
        for alias in self.aliases:
            formats.add(normalize_cad_format(alias))
        return {value for value in formats if value}

    def normalized_extensions(self) -> set[str]:
        return {ext.lower().lstrip(".") for ext in self.extensions}


class CadConnector:
    info: CadConnectorInfo

    def __init__(self, info: CadConnectorInfo):
        self.info = info

    def match_extension(self, extension: str) -> bool:
        ext = extension.lower().lstrip(".")
        return ext in self.info.normalized_extensions()

    def match_format(self, cad_format: str) -> bool:
        normalized = normalize_cad_format(cad_format)
        return normalized in self.info.normalized_formats()

    def extract_attributes(
        self,
        file_path: str,
        *,
        filename: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> Dict[str, object]:
        return {}


class StaticCadConnector(CadConnector):
    def __init__(self, info: CadConnectorInfo, attributes: Optional[Dict[str, object]] = None):
        super().__init__(info)
        self._attributes = dict(attributes or {})

    def extract_attributes(
        self,
        file_path: str,
        *,
        filename: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> Dict[str, object]:
        return dict(self._attributes)


class KeyValueCadConnector(CadConnector):
    """Extract attributes from simple key=value or key: value text blocks."""

    _max_bytes = 256 * 1024

    def __init__(self, info: CadConnectorInfo, key_aliases: Optional[Dict[str, str]] = None):
        super().__init__(info)
        self._key_aliases = {
            self._normalize_key(k): v for k, v in (key_aliases or {}).items()
        }

    def extract_attributes(
        self,
        file_path: str,
        *,
        filename: Optional[str] = None,
        content: Optional[bytes] = None,
    ) -> Dict[str, object]:
        raw = content
        if raw is None:
            try:
                with open(file_path, "rb") as f:
                    raw = f.read(self._max_bytes)
            except OSError:
                return {}
        else:
            raw = raw[: self._max_bytes]

        try:
            text = raw.decode("utf-8", errors="ignore")
        except Exception:
            return {}

        attrs: Dict[str, object] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
            elif ":" in line:
                key, value = line.split(":", 1)
            else:
                continue
            key_norm = self._normalize_key(key)
            canonical = self._key_aliases.get(key_norm)
            if not canonical:
                continue
            value = value.strip().strip('"').strip("'")
            if not value:
                continue
            if canonical == "weight":
                attrs[canonical] = self._parse_weight(value)
            else:
                attrs[canonical] = value
        return attrs

    @staticmethod
    def _parse_weight(raw: object) -> object:
        if isinstance(raw, (int, float)):
            return float(raw)
        text = str(raw).strip()
        if not text:
            return raw
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text)
        if not match:
            return raw
        number = match.group(0).replace(",", "")
        try:
            value = float(number)
        except ValueError:
            return raw
        unit = text[match.end():].strip().lower()
        if unit:
            if unit.startswith("kg") or "公斤" in unit:
                return value
            if unit.startswith("g") and not unit.startswith("kg"):
                return value / 1000.0
            if unit.startswith("t") or "吨" in unit:
                return value * 1000.0
        return value

    @staticmethod
    def _normalize_key(key: str) -> str:
        return normalize_cad_key(key)


def build_simple_connector(
    *,
    connector_id: str,
    label: str,
    cad_format: str,
    document_type: str,
    extensions: Iterable[str],
    aliases: Optional[Iterable[str]] = None,
    priority: int = 0,
    description: Optional[str] = None,
    signature_tokens: Optional[Iterable[str]] = None,
) -> CadConnector:
    return StaticCadConnector(
        CadConnectorInfo(
            id=connector_id,
            label=label,
            cad_format=cad_format,
            document_type=document_type,
            extensions=tuple(extensions),
            aliases=tuple(aliases or ()),
            priority=priority,
            description=description,
            signature_tokens=tuple(signature_tokens or ()),
        )
    )


def build_keyvalue_connector(
    *,
    connector_id: str,
    label: str,
    cad_format: str,
    document_type: str,
    extensions: Iterable[str],
    aliases: Optional[Iterable[str]] = None,
    priority: int = 0,
    description: Optional[str] = None,
    key_aliases: Optional[Dict[str, str]] = None,
    signature_tokens: Optional[Iterable[str]] = None,
) -> CadConnector:
    return KeyValueCadConnector(
        CadConnectorInfo(
            id=connector_id,
            label=label,
            cad_format=cad_format,
            document_type=document_type,
            extensions=tuple(extensions),
            aliases=tuple(aliases or ()),
            priority=priority,
            description=description,
            signature_tokens=tuple(signature_tokens or ()),
        ),
        key_aliases=key_aliases,
    )
