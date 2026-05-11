#!/usr/bin/env python3
"""Fixture verification for CAD material field mapping without AutoCAD.

The script parses the alias table from CadMaterialFieldMapper.cs, then applies
the same extraction and table-update rules to a JSON mock drawing fixture.
"""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PLUGIN = ROOT / "CADDedupPlugin"
FIXTURE = ROOT / "fixtures" / "material_sync_mock_drawing.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_aliases() -> dict[str, str]:
    text = read(PLUGIN / "CadMaterialFieldMapper.cs")
    pairs = re.findall(r'\{\s*"([^"]+)",\s*"([^"]+)"\s*\}', text)
    require(pairs, "no aliases parsed from CadMaterialFieldMapper.cs")
    return {canonical_key(raw, {}): canonical for raw, canonical in pairs}


def canonical_key(raw: Any, aliases: dict[str, str]) -> str:
    if raw is None:
        return ""
    compact = (
        str(raw)
        .strip()
        .replace(" ", "")
        .replace("\t", "")
        .replace("-", "_")
        .replace("：", "")
        .replace(":", "")
        .lower()
    )
    return aliases.get(compact, compact)


def add_field(fields: dict[str, str], raw_key: Any, value: Any, aliases: dict[str, str]) -> bool:
    if raw_key is None or value is None:
        return False
    raw_value = value_to_string(value).strip()
    if not str(raw_key).strip() or not raw_value:
        return False
    key = canonical_key(raw_key, aliases)
    if key:
        fields[key] = raw_value
        return True
    return False


def extract_fields(fixture: dict[str, Any], aliases: dict[str, str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for block in fixture.get("blocks", []):
        for raw_key, value in block.get("attributes", {}).items():
            add_field(fields, raw_key, value, aliases)

    for table in fixture.get("tables", []):
        for row in table:
            col = 0
            while col < len(row):
                text = row[col]
                if not str(text).strip():
                    col += 1
                    continue
                text_value = str(text)
                if "=" in text_value and text_value.index("=") > 0:
                    raw_key, value = text_value.split("=", 1)
                    add_field(fields, raw_key, value, aliases)
                    col += 1
                    continue
                if col + 1 < len(row):
                    if add_field(fields, text_value, row[col + 1], aliases):
                        col += 1
                col += 1
    return fields


def normalize_input(fields: dict[str, Any], aliases: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for raw_key, value in fields.items():
        key = canonical_key(raw_key, aliases)
        text = value_to_string(value)
        if key and text.strip():
            normalized[key] = text
    return normalized


def value_to_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def apply_table(table: list[list[str]], fields: dict[str, Any], aliases: dict[str, str]) -> int:
    normalized = normalize_input(fields, aliases)
    updated = 0
    for row_index, row in enumerate(table):
        col_index = 0
        while col_index < len(row):
            text = row[col_index]
            if not str(text).strip():
                col_index += 1
                continue
            text_value = str(text)
            if "=" in text_value and text_value.index("=") > 0:
                raw_key = text_value.split("=", 1)[0]
                key = canonical_key(raw_key, aliases)
                if key in normalized:
                    new_value = f"{raw_key}={normalized[key]}"
                    if table[row_index][col_index] != new_value:
                        table[row_index][col_index] = new_value
                        updated += 1
                    col_index += 1
                    continue
            if col_index + 1 < len(row):
                key = canonical_key(text_value, aliases)
                if key in normalized and table[row_index][col_index + 1] != normalized[key]:
                    table[row_index][col_index + 1] = normalized[key]
                    updated += 1
                    col_index += 1
            col_index += 1
    return updated


def apply_fields(fixture: dict[str, Any], aliases: dict[str, str]) -> int:
    normalized = normalize_input(fixture.get("apply_fields", {}), aliases)
    updated = 0
    for block in fixture.get("blocks", []):
        attributes = block.get("attributes", {})
        for raw_key, value in list(attributes.items()):
            key = canonical_key(raw_key, aliases)
            if key in normalized and value != normalized[key]:
                attributes[raw_key] = normalized[key]
                updated += 1

    for table in fixture.get("tables", []):
        updated += apply_table(table, fixture.get("apply_fields", {}), aliases)
    return updated


def main() -> int:
    aliases = load_aliases()
    fixture = json.loads(read(FIXTURE))

    extracted = extract_fields(fixture, aliases)
    require(extracted == fixture["expected_extract"], f"unexpected extract: {extracted}")

    working = deepcopy(fixture)
    updated = apply_fields(working, aliases)
    require(updated == fixture["expected_updates"], f"unexpected update count: {updated}")
    require(
        working["tables"][0] == fixture["expected_table_after"],
        f"unexpected table after apply: {working['tables'][0]}",
    )

    print("OK: material sync mock drawing fixture passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
