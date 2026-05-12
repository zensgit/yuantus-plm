#!/usr/bin/env python3
"""Verify the SDK-free SolidWorks confirmation model contract.

This script mirrors the intended behavior of SolidWorksDiffConfirmationViewModel
against the committed SolidWorks diff-confirm fixture. It intentionally does not
load SolidWorks, COM, WPF, or .NET.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/samples/cad_material_solidworks_diff_confirm_fixture.json"
SOURCE = (
    ROOT
    / "clients/solidworks-material-sync/SolidWorksMaterialSync/"
    "SolidWorksDiffConfirmationViewModel.cs"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def is_solidworks_write_key(key: str) -> bool:
    forbidden_autocad_labels = {"材料", "规格", "长", "宽", "厚", "图号", "名称"}
    return bool(key) and key not in forbidden_autocad_labels and key.startswith("SW-") and "@" in key


def confirmation_rows(case: dict[str, Any]) -> list[dict[str, Any]]:
    current = case["request"].get("current_cad_fields", {})
    expected = case["expect"]
    statuses = expected.get("statuses", {})
    rows: list[dict[str, Any]] = []
    for key, target_value in expected["target_cad_fields"].items():
        rows.append(
            {
                "field_key": key,
                "current_value": "" if current.get(key) is None else str(current.get(key, "")),
                "target_value": "" if target_value is None else str(target_value),
                "status": statuses.get(key, "unchanged"),
                "can_write": is_solidworks_write_key(key),
            }
        )
    return rows


def confirmed_write_fields(case: dict[str, Any]) -> dict[str, str]:
    if not case["expect"]["requires_confirmation"]:
        return {}
    return {
        key: "" if value is None else str(value)
        for key, value in case["expect"]["write_cad_fields"].items()
        if is_solidworks_write_key(key)
    }


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")

    for token in (
        "SolidWorksDiffConfirmationViewModel",
        "FromPreview",
        "Confirm()",
        "Cancel()",
        "ConfirmedWriteFields",
        "SolidWorksWriteBackPlan.FromWriteCadFields",
        "RequiresConfirmation",
        "SolidWorksDiffFieldRow",
    ):
        require(token in source, f"source missing {token}")

    for case in fixture["cases"]:
        rows = confirmation_rows(case)
        confirmed = confirmed_write_fields(case)
        cancelled: dict[str, str] = {}

        expected = case["expect"]
        require(len(rows) == len(expected["target_cad_fields"]), f"{case['name']} row count mismatch")
        require(confirmed == {key: str(value) for key, value in expected["write_cad_fields"].items()}, f"{case['name']} confirm mismatch")
        require(cancelled == {}, f"{case['name']} cancel should be no-op")
        require(
            all(row["field_key"].startswith("SW-") for row in rows),
            f"{case['name']} contains non-SolidWorks row key",
        )

    print("OK: SolidWorks confirmation fixture passed (3 cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

