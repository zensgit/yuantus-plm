#!/usr/bin/env python3
"""Validate SolidWorks CAD Material Sync Windows evidence before acceptance."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = (
    ROOT / "docs/CAD_MATERIAL_SYNC_SOLIDWORKS_WINDOWS_VALIDATION_EVIDENCE_TEMPLATE_20260511.md"
)

PLACEHOLDER_VALUES = {
    "",
    "no",
    "pending",
    "yes | no",
    "confirm | cancel",
    "add-in manager | registry | manual debug load",
    "todo",
    "tbd",
    "n/a",
    "na",
    "none",
}

SECRET_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r"\b(api[_-]?key|token|password|secret)\s*[:=]\s*\S+", re.IGNORECASE),
)

FORBIDDEN_EVIDENCE_VALUE_TOKENS = (
    "mock fixture",
    "synthetic",
    "production customer",
)

FORBIDDEN_WRITE_PACKAGE_TOKENS = (
    "材料",
    "材质",
    "规格",
    "物料规格",
    "长",
    "长度",
    "宽",
    "宽度",
    "厚",
    "厚度",
)

REQUIRED_PRIMARY_FIELDS = (
    "Operator",
    "Review date",
    "Windows version",
    "SolidWorks primary version",
    "SolidWorks service pack",
    "Yuantus base URL",
    "Yuantus commit",
    "Test SolidWorks document description",
    "Build command",
    "Build result",
    "Compiled add-in DLL path",
    "Add-in manifest or registration path",
    "Load method",
    "Loaded add-in path",
    "SolidWorks add-in load result",
    "SolidWorks add-in log path",
    "Profile fetch result",
    "Property read command result",
    "Diff preview UI result",
    "Confirm write command result",
    "Cancel path result",
    "SolidWorks document description",
    "Custom property read result",
    "Cut-list or table read result",
    "Read SW-Material@Part value",
    "Read SW-Specification@Part value",
    "Read SW-Length@Part or @CutList value",
    "Read SW-Width@Part or @CutList value",
    "Read SW-Thickness@Part value",
    "Before SW-Material@Part value",
    "Before SW-Specification@Part value",
    "Diff preview screenshot path",
    "Write package JSON path",
    "User action",
    "After SW-Material@Part value",
    "After SW-Specification@Part value",
    "Save/reopen result",
    "Yuantus dry-run log path",
    "Yuantus real-write log path",
    "Reviewer",
    "Decision date",
    "Reason",
)

REQUIRED_REGRESSION_FIELDS = (
    "SolidWorks regression version",
    "SolidWorks regression service pack",
    "SolidWorks regression build result",
    "SolidWorks regression load result",
    "SolidWorks regression field read result",
    "SolidWorks regression write-back result",
)


def _normalize(value: str) -> str:
    return value.strip().strip("`").strip()


def _is_placeholder(value: str) -> bool:
    normalized = _normalize(value)
    if normalized.lower() in PLACEHOLDER_VALUES:
        return True
    if normalized.startswith("<") and normalized.endswith(">"):
        return True
    return False


def _extract_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z0-9 @/._-]+):\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = _normalize(match.group(2))
        fields[key] = value
    return fields


def _add_if(condition: bool, failures: list[str], message: str) -> None:
    if condition:
        failures.append(message)


def _field(fields: dict[str, str], name: str) -> str:
    return fields.get(name, "")


def _require_field(fields: dict[str, str], failures: list[str], name: str) -> None:
    value = _field(fields, name)
    _add_if(_is_placeholder(value), failures, f"{name} must be filled")


def _require_yes(fields: dict[str, str], failures: list[str], name: str) -> None:
    value = _field(fields, name).lower()
    _add_if(value != "yes", failures, f"{name} must be yes")


def _validate_no_secrets(fields: dict[str, str], failures: list[str]) -> None:
    for name, value in fields.items():
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                failures.append(f"{name} appears to contain a plaintext secret")
                break


def _validate_no_fake_evidence_values(fields: dict[str, str], failures: list[str]) -> None:
    for name, value in fields.items():
        lowered = value.lower()
        for token in FORBIDDEN_EVIDENCE_VALUE_TOKENS:
            if token in lowered:
                failures.append(f"{name} appears to contain non-real evidence: {token}")
                break


def _validate_no_autocad_write_keys(fields: dict[str, str], failures: list[str]) -> None:
    value = _field(fields, "Write package JSON path")
    for token in FORBIDDEN_WRITE_PACKAGE_TOKENS:
        if token in value:
            failures.append(f"Write package JSON path appears to contain AutoCAD field key: {token}")
            break


def validate(text: str, *, require_regression: bool = False) -> list[str]:
    fields = _extract_fields(text)
    failures: list[str] = []

    for name in REQUIRED_PRIMARY_FIELDS:
        _require_field(fields, failures, name)

    _add_if(
        "solidworks" not in _field(fields, "SolidWorks primary version").lower(),
        failures,
        "SolidWorks primary version must identify SolidWorks",
    )
    _add_if(
        not _field(fields, "Compiled add-in DLL path").lower().endswith(".dll"),
        failures,
        "Compiled add-in DLL path must reference a .dll file",
    )
    _add_if(
        _field(fields, "User action").lower() != "confirm",
        failures,
        "User action must be confirm for write-back acceptance",
    )
    _add_if(
        _field(fields, "Before SW-Specification@Part value")
        == _field(fields, "After SW-Specification@Part value"),
        failures,
        "Before/after SW-Specification@Part values must differ",
    )

    for name in (
        "SolidWorks field read complete",
        "SolidWorks local confirmation UI complete",
        "Real SolidWorks write-back validated",
        "Windows SolidWorks runtime accepted",
    ):
        _require_yes(fields, failures, name)

    _add_if(
        _field(fields, "Decision").lower() != "accept",
        failures,
        "Decision must be accept after reviewer approval",
    )

    regression_complete = _field(fields, "SolidWorks regression complete").lower()
    if require_regression or regression_complete == "yes":
        _add_if(
            regression_complete != "yes",
            failures,
            "SolidWorks regression complete must be yes",
        )
        for name in REQUIRED_REGRESSION_FIELDS:
            _require_field(fields, failures, name)

    _validate_no_secrets(fields, failures)
    _validate_no_fake_evidence_values(fields, failures)
    _validate_no_autocad_write_keys(fields, failures)
    return failures


def _json_report(evidence_path: Path, failures: list[str], *, require_regression: bool) -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "ok": not failures,
            "evidence": str(evidence_path),
            "require_regression": require_regression,
            "failure_count": len(failures),
            "failures": failures,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a filled SolidWorks CAD Material Sync Windows evidence markdown file. "
            "This validates evidence shape only; it does not run SolidWorks."
        )
    )
    parser.add_argument(
        "evidence",
        nargs="?",
        default=str(DEFAULT_TEMPLATE),
        help="Path to the filled evidence markdown file",
    )
    parser.add_argument(
        "--require-regression",
        action="store_true",
        help="also require the optional SolidWorks regression section to be complete",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a redaction-safe machine-readable result",
    )
    args = parser.parse_args(argv)

    evidence_path = Path(args.evidence)
    if not evidence_path.is_file():
        failures = [f"evidence file does not exist: {evidence_path}"]
        if args.json:
            print(_json_report(evidence_path, failures, require_regression=args.require_regression))
        else:
            print(f"FAIL: {failures[0]}", file=sys.stderr)
        return 1

    failures = validate(
        evidence_path.read_text(encoding="utf-8", errors="replace"),
        require_regression=args.require_regression,
    )
    if args.json:
        print(_json_report(evidence_path, failures, require_regression=args.require_regression))
        return 1 if failures else 0

    if failures:
        print("FAIL: CAD material SolidWorks Windows evidence is not acceptable")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("OK: CAD material SolidWorks Windows evidence shape is acceptable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
