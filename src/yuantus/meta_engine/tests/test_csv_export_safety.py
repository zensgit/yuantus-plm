"""Unit tests for the CSV formula-injection guard and the safe writer factories.

Locks three properties relied on by every export that routes through this module:
1. ``neutralize_csv_formula`` quote-prefixes formula/control-leading text and ONLY that;
2. it passes non-strings (ints/floats/None/bool) through untouched so numeric cells stay numeric;
3. ``safe_writer``/``safe_dict_writer`` are drop-in for ``csv.writer``/``csv.DictWriter`` —
   hostile cells are neutralized while benign rows stay byte-identical to the unguarded writer.
"""
from __future__ import annotations

import csv
from io import StringIO

import pytest

from yuantus.meta_engine.web.csv_export_safety import (
    neutralize_csv_formula,
    safe_dict_writer,
    safe_writer,
)


@pytest.mark.parametrize("payload", ["=1+1", "+1", "-1+1", "@SUM(A1)", "\tx", "\rx", "\nx", "  =evil()"])
def test_neutralizes_formula_and_control_prefixes(payload):
    assert neutralize_csv_formula(payload) == "'" + payload


@pytest.mark.parametrize("benign", ["Part", "Document", "released", "draft 2", "ACME-001", "已发布", "a-b", "x@y"])
def test_leaves_benign_text_unchanged(benign):
    assert neutralize_csv_formula(benign) == benign


def test_passes_non_strings_through_untouched():
    for v in (None, 0, 5, -5, 3.14, True):
        assert neutralize_csv_formula(v) == v
    # a negative NUMBER (not a string) is never quoted -> spreadsheets keep it numeric
    assert neutralize_csv_formula(-5) == -5


def test_negative_number_as_string_is_quoted():
    # the known, accepted trade-off: a negative number rendered as TEXT looks like a formula prefix
    assert neutralize_csv_formula("-5") == "'-5"


def test_safe_writer_neutralizes_cells_but_keeps_benign_bytes_identical():
    hostile, plain = StringIO(), StringIO()
    sw = safe_writer(hostile, lineterminator="\n")
    pw = csv.writer(plain, lineterminator="\n")
    rows = [["name", "qty"], ["=1+2", 3], ["Part", 5]]
    for r in rows:
        sw.writerow(r)
        pw.writerow(r)
    s = hostile.getvalue().splitlines()
    p = plain.getvalue().splitlines()
    assert s[1] == "'=1+2,3"            # hostile leading-= cell neutralized
    assert s[0] == p[0] == "name,qty"   # benign header byte-identical to unguarded writer
    assert s[2] == p[2] == "Part,5"     # benign + numeric row byte-identical


def test_safe_writer_writerows_neutralizes_all():
    buf = StringIO()
    safe_writer(buf, lineterminator="\n").writerows([["@evil"], ["ok"]])
    lines = buf.getvalue().splitlines()
    assert lines == ["'@evil", "ok"]


def test_safe_dict_writer_neutralizes_values_benign_header_noop():
    buf = StringIO()
    w = safe_dict_writer(buf, fieldnames=["name", "count"], lineterminator="\n")
    w.writeheader()
    w.writerow({"name": "=HYPERLINK(1)", "count": 7})
    w.writerow({"name": "Widget", "count": 2})
    lines = buf.getvalue().splitlines()
    assert lines[0] == "name,count"        # benign constant field names -> no-op
    assert lines[1] == "'=HYPERLINK(1),7"  # hostile value neutralized
    assert lines[2] == "Widget,2"          # benign byte-identical


def test_safe_dict_writer_neutralizes_hostile_header():
    # a data-derived fieldname that is itself a formula must not smuggle into the header row
    buf = StringIO()
    w = safe_dict_writer(buf, fieldnames=["=evil", "ok"], lineterminator="\n")
    w.writeheader()
    assert buf.getvalue().splitlines()[0] == "'=evil,ok"


def test_safe_dict_writer_forwards_constructor_kwargs():
    # kwargs such as extrasaction='ignore' must reach the underlying csv.DictWriter
    buf = StringIO()
    w = safe_dict_writer(buf, fieldnames=["a"], extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerow({"a": "=x", "b": "dropped"})
    lines = buf.getvalue().splitlines()
    assert lines == ["a", "'=x"]
