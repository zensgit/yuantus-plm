#!/usr/bin/env python3
"""Verify the SDK-free SolidWorks pull workflow contract.

The workflow modeled here is:

field snapshot -> /diff/preview -> confirmation model -> confirm/cancel ->
gateway apply boundary.

It intentionally does not load SolidWorks, COM, WPF, .NET, or a real server.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "docs/samples/cad_material_solidworks_diff_confirm_fixture.json"
WORKFLOW = (
    ROOT
    / "clients/solidworks-material-sync/SolidWorksMaterialSync/"
    "SolidWorksMaterialPullWorkflow.cs"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def solidworks_write_plan(write_cad_fields: dict[str, Any]) -> dict[str, str]:
    forbidden = {"材料", "规格", "长", "宽", "厚", "图号", "名称"}
    return {
        key: "" if value is None else str(value)
        for key, value in write_cad_fields.items()
        if key.startswith("SW-") and "@" in key and key not in forbidden
    }


def confirm_and_apply(case: dict[str, Any]) -> dict[str, str]:
    expect = case["expect"]
    if not expect["requires_confirmation"]:
        return {}
    return solidworks_write_plan(expect["write_cad_fields"])


def cancel(case: dict[str, Any]) -> dict[str, str]:
    return {}


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    for token in (
        "SolidWorksMaterialPullWorkflow",
        "PreviewAsync",
        "SolidWorksDiffPreviewClient",
        "PreviewAsync<SolidWorksDiffPreviewResult>",
        "SolidWorksDiffConfirmationViewModel.FromPreview",
        "ConfirmAndApply",
        "confirmation.Confirm()",
        "fieldAdapter.ApplyFields",
        "Cancel(",
        "confirmation?.Cancel()",
    ):
        require(token in source, f"workflow source missing {token}")

    for forbidden in ("win32com", "pythoncom", "SldWorks.Application", "dotnet"):
        require(forbidden not in source, f"workflow source should not mention {forbidden}")

    cases = {case["name"]: case for case in fixture["cases"]}

    changed = cases["solidworks_sheet_add_thickness_and_change_specification"]
    require(
        confirm_and_apply(changed)
        == {"SW-Specification@Part": "1200*600*12", "SW-Thickness@Part": "12"},
        "changed case should apply only confirmed SolidWorks write fields",
    )
    require(cancel(changed) == {}, "changed case cancel should be no-op")

    noop = cases["solidworks_noop_requires_no_confirmation"]
    require(confirm_and_apply(noop) == {}, "noop case should not apply writes")

    cleared = cases["solidworks_explicit_clear_custom_property"]
    require(
        confirm_and_apply(cleared) == {"SW-Coating@Part": ""},
        "explicit clear should preserve empty string write",
    )
    require(cancel(cleared) == {}, "explicit clear cancel should be no-op")

    print("OK: SolidWorks pull workflow fixture passed (3 cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

