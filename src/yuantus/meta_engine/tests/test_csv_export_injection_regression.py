"""Regression: every wired CSV export choke point neutralizes formula injection.

These exercise the REAL export builders (the pure, DB-free ones), not just the
``safe_writer``/``safe_dict_writer`` factory — so a builder still calling the bare
``csv.writer``/``csv.DictWriter`` would FAIL here even though the factory unit test passes.
"""
from __future__ import annotations

from yuantus.meta_engine.approvals.service import ApprovalService
from yuantus.meta_engine.subcontracting.service import SubcontractingService
from yuantus.meta_engine.web.bom_compare_router import _diff_to_csv, _rows_to_csv
from yuantus.meta_engine.web.impact_router import _csv_bytes as impact_csv_bytes
from yuantus.meta_engine.web.item_cockpit_router import _csv_bytes as cockpit_csv_bytes
from yuantus.meta_engine.web.release_readiness_router import _csv_bytes as readiness_csv_bytes

EVIL = "=1+2"


def test_bom_compare_rows_to_csv_neutralizes_line_key():
    out = _rows_to_csv([{"line_key": EVIL, "parent_id": "p", "child_id": "c"}])
    assert "'=1+2" in out
    # the raw formula never appears as an unguarded leading cell
    assert "\n=1+2" not in out


def test_bom_compare_diff_to_csv_neutralizes_cells():
    out = _diff_to_csv({"differences": [{"change_type": EVIL, "row_key": "@evil"}]})
    assert "'=1+2" in out
    assert "'@evil" in out


def test_item_cockpit_csv_bytes_neutralizes_values():
    assert b"'=1+2" in cockpit_csv_bytes(rows=[{"name": EVIL}], columns=["name"])


def test_impact_csv_bytes_neutralizes_values():
    assert b"'=1+2" in impact_csv_bytes(rows=[{"name": EVIL}], columns=["name"])


def test_release_readiness_csv_bytes_neutralizes_values():
    assert b"'=1+2" in readiness_csv_bytes(rows=[{"name": EVIL}], columns=["name"])


def test_subcontracting_render_csv_neutralizes_values():
    out = SubcontractingService._render_csv([{"vendor_name": EVIL}], ["vendor_name"])
    assert "'=1+2" in out


def test_approvals_render_csv_neutralizes_values():
    out = ApprovalService._render_csv([{"title": EVIL}], ["title"])
    assert "'=1+2" in out


def _csv_cells(text):
    import csv
    from io import StringIO
    return [c for row in csv.reader(StringIO(text)) for c in row]


def test_bom_compare_rows_to_csv_comma_value_cannot_restore_formula():
    # The hand-built builders must csv-QUOTE, not bare ",".join: a value with an embedded comma
    # must stay ONE cell, never split so its tail ("=1+2") becomes a live formula cell.
    out = _rows_to_csv([{"line_key": "safe,=1+2", "parent_id": "p"}])
    cells = _csv_cells(out)
    assert "safe,=1+2" in cells  # csv quoting kept the comma value as a single cell
    assert not any(c.startswith(("=", "+", "-", "@")) for c in cells)  # no live-formula cell


def test_bom_compare_diff_to_csv_comma_value_cannot_restore_formula():
    out = _diff_to_csv({"differences": [{"change_type": "x", "row_key": "safe,=1+2"}]})
    cells = _csv_cells(out)
    assert "safe,=1+2" in cells
    assert not any(c.startswith(("=", "+", "-", "@")) for c in cells)
